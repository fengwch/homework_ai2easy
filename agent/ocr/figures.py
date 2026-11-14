"""
题目插图的检测、截取与保存。
支持两种模式：
1. 按题目 + 按「如图」：传入 ocr_lines 与 questions，生成文字 mask，排除文字区域后截取图块，按题目垂直位置分配。
2. 整图检测（兼容）：无 ocr_lines 时退化为 extract_and_save_figures，从整图检测插图区域。
保存时强制使用 .png 后缀，并对文件做后缀与内容校验。
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from utils.logging import get_logger

logger = get_logger(__name__)

# 插图保存根目录，可由环境变量 OCR_FIGURES_DIR 覆盖
DEFAULT_FIGURES_DIR = "uploads/ocr_figures"
# 返回给前端的 URL 前缀
FIGURES_URL_PREFIX = os.getenv("OCR_FIGURES_URL_PREFIX", "/uploads/ocr_figures")

# 校验：最小文件大小（字节），过小视为无效
MIN_FILE_SIZE_BYTES = 100
# 校验：图片至少有一定比例非白像素（避免保存空白图）
MIN_NON_WHITE_RATIO = 0.005
WHITE_THRESHOLD = 250

VALID_IMAGE_EXT = ".png"

# 按题截图：文字框扩展像素（避免裁到字边）
TEXT_BOX_PADDING = 3
# 与文字 mask 重叠比例超过此值视为文字区域，排除
TEXT_OVERLAP_RATIO_THRESHOLD = 0.35


def _get_figures_dir() -> Path:
    d = os.getenv("OCR_FIGURES_DIR", DEFAULT_FIGURES_DIR)
    path = Path(d)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_text_mask(
    H: int, W: int, ocr_lines: List[Dict[str, Any]], padding: int = TEXT_BOX_PADDING
) -> Optional["np.ndarray"]:
    """
    根据 OCR 行框生成文字区域 mask（255=文字，0=非文字）。
    若所有行的 box 均为 None，返回 None。
    """
    boxes_with_pos = [line for line in ocr_lines if line.get("box") is not None]
    if not boxes_with_pos:
        return None
    mask = np.zeros((H, W), dtype=np.uint8)
    for line in boxes_with_pos:
        x, y, w, h = line["box"]
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(W, x + w + padding)
        y2 = min(H, y + h + padding)
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 255
    return mask


def _merge_overlapping_boxes(
    boxes: List[Tuple[int, int, int, int]],
    overlap_threshold: float = 0.3,
) -> List[Tuple[int, int, int, int]]:
    """合并垂直重叠或过近的框。"""
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: (b[0], b[1]))
    merged = [list(boxes[0])]
    for y, x, w, h in boxes[1:]:
        my, mx, mw, mh = merged[-1]
        y2_cur = y + h
        y2_prev = my + mh
        overlap_y = max(0, min(y2_cur, y2_prev) - max(y, my))
        min_h = min(h, mh)
        if min_h > 0 and overlap_y / min_h >= overlap_threshold:
            ny = min(y, my)
            nx = min(x, mx)
            merged[-1] = [ny, nx, max(x + w, mx + mw) - nx, max(y2_cur, y2_prev) - ny]
        else:
            merged.append([y, x, w, h])
    return [tuple(b) for b in merged]


def _is_valid_image_file(file_path: Path) -> bool:
    """
    校验是否为有效图片文件：后缀 .png、存在、大小达标、可被 PIL 打开且非几乎全白。
    任一不通过返回 False。
    """
    if not file_path.suffix.lower() == VALID_IMAGE_EXT:
        logger.warning("插图文件后缀非 .png: %s", file_path)
        return False
    if not file_path.is_file():
        logger.warning("插图路径不是文件: %s", file_path)
        return False
    if file_path.stat().st_size < MIN_FILE_SIZE_BYTES:
        logger.warning("插图文件过小: %s (%s bytes)", file_path, file_path.stat().st_size)
        return False
    try:
        img = Image.open(file_path)
        img.load()
        arr = np.array(img)
    except Exception as e:
        logger.warning("插图文件无法作为图片打开: %s %s", file_path, e)
        return False
    if arr.size == 0:
        return False
    if len(arr.shape) == 3:
        gray = np.mean(arr, axis=2)
    else:
        gray = arr
    non_white = np.sum(gray < WHITE_THRESHOLD)
    ratio = non_white / gray.size
    if ratio < MIN_NON_WHITE_RATIO:
        logger.warning("插图内容几乎全白，视为无效: %s (non_white_ratio=%.4f)", file_path, ratio)
        return False
    return True


def extract_and_save_figures(
    img_array: np.ndarray,
    run_id: str,
) -> List[str]:
    """
    从整图中检测插图区域，裁剪并保存为 .png 文件；仅将后缀与内容校验通过的图片加入返回列表。
    - 保存路径：<figures_dir>/<run_id>/0.png, 1.png, ...
    - 返回：通过校验的图片的 URL 列表，如 ["/uploads/ocr_figures/<run_id>/0.png", ...]
    """
    import cv2

    figures_dir = _get_figures_dir()
    run_dir = figures_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    prefix = FIGURES_URL_PREFIX.strip("/")
    if not prefix:
        prefix = "uploads/ocr_figures"
    url_prefix = "/" + prefix + "/" + run_id

    H, W = img_array.shape[:2]
    if H < 10 or W < 10:
        logger.debug("图像过小，跳过插图检测")
        return []

    # 转灰度、二值化、反转（检测黑色绘图区域）
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(binary, kernel)
    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 20 or h < 20:
            continue
        if w > W * 0.95 and h > H * 0.95:
            continue
        roi = binary[y : y + h, x : x + w]
        black_ratio = np.sum(roi > 0) / (roi.size or 1)
        if black_ratio < 0.02:
            continue
        boxes.append((y, x, w, h))

    boxes = _merge_overlapping_boxes(boxes)
    urls = []

    for i, (y, x, w, h) in enumerate(boxes):
        # 确保是图片区域（numpy 切片）
        y1, y2 = max(0, y), min(H, y + h)
        x1, x2 = max(0, x), min(W, x + w)
        if y2 <= y1 or x2 <= x1:
            continue
        crop = img_array[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        # 固定使用 .png 后缀
        filename = f"{i}{VALID_IMAGE_EXT}"
        file_path = run_dir / filename
        try:
            # 保存为 PNG 文件（不是目录）
            pil_img = Image.fromarray(crop)
            pil_img.save(file_path, format="PNG")
        except Exception as e:
            logger.warning("保存插图失败 %s: %s", file_path, e)
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass
            continue
        if not _is_valid_image_file(file_path):
            try:
                file_path.unlink()
            except OSError:
                pass
            continue
        urls.append(f"{url_prefix}/{filename}")

    logger.info("插图截取完成 run_id=%s 保存=%s 通过校验=%s", run_id, len(boxes), len(urls))
    return urls


def extract_figures_for_questions(
    img_array: np.ndarray,
    ocr_lines: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    run_id: str,
) -> Dict[str, List[str]]:
    """
    按题目、按「如图」截取插图，尽量排除文字区域。
    - 用 ocr_lines 的 box 生成文字 mask，检测到的图块与文字重叠过大的排除。
    - 将图块按垂直位置分配给含「如图」的题目（figureRefLineIndex 对齐）。
    返回 question_id -> [url, ...]，仅包含通过校验的 .png URL。
    若 ocr_lines 无有效 box，退化为整图检测并均分到各题（与旧逻辑兼容）。
    """
    import cv2

    H, W = img_array.shape[:2]
    if H < 10 or W < 10:
        return {q.get("id", f"q{i+1}"): [] for i, q in enumerate(questions)}

    text_mask = _build_text_mask(H, W, ocr_lines)
    has_text_mask = text_mask is not None and np.any(text_mask > 0)

    # 检测图块：灰度、二值反转、轮廓
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(binary, kernel)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    figure_boxes = []  # (y, x, w, h)
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 20 or h < 20:
            continue
        if w > W * 0.95 and h > H * 0.95:
            continue
        roi = binary[y : y + h, x : x + w]
        black_ratio = np.sum(roi > 0) / (roi.size or 1)
        if black_ratio < 0.02:
            continue
        if has_text_mask:
            patch = text_mask[y : y + h, x : x + w]
            overlap = np.sum(patch > 0) / (patch.size or 1)
            if overlap >= TEXT_OVERLAP_RATIO_THRESHOLD:
                continue
        figure_boxes.append((y, x, w, h))

    figure_boxes = _merge_overlapping_boxes(figure_boxes)

    # 题目对应的参考 Y 坐标（用于分配图块）
    def _ref_y_for_question(q: Dict[str, Any]) -> Optional[float]:
        idx = (q.get("metadata") or {}).get("figureRefLineIndex")
        if idx is None or idx < 0 or not ocr_lines or idx >= len(ocr_lines):
            return None
        box = ocr_lines[idx].get("box")
        if not box:
            return None
        _, y, _, h = box
        return y + h / 2.0

    # 只给有「如图」的题分配图块；按与题目参考 Y 的垂直距离
    q_with_ref = [(q, _ref_y_for_question(q)) for q in questions if (q.get("metadata") or {}).get("hasImageRef")]
    if not q_with_ref and figure_boxes:
        q_with_ref = [(q, _ref_y_for_question(q)) for q in questions]

    figures_dir = _get_figures_dir()
    run_dir = figures_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    prefix = FIGURES_URL_PREFIX.strip("/") or "uploads/ocr_figures"
    url_prefix = "/" + prefix + "/" + run_id

    out: Dict[str, List[str]] = {q.get("id", f"q{i+1}"): [] for i, q in enumerate(questions)}

    for (y, x, w, h) in figure_boxes:
        y1, y2 = max(0, y), min(H, y + h)
        x1, x2 = max(0, x), min(W, x + w)
        if y2 <= y1 or x2 <= x1:
            continue
        crop = img_array[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        center_y = (y1 + y2) / 2.0

        # 分配给垂直距离最近的题目（有 figureRef 的优先）
        best_qid: Optional[str] = None
        best_dist: Optional[float] = None
        for q, ref_y in q_with_ref:
            if ref_y is not None:
                d = abs(center_y - ref_y)
                if best_dist is None or d < best_dist:
                    best_dist = d
                    best_qid = q.get("id")
            elif best_qid is None:
                best_qid = q.get("id")
        if best_qid is None and questions:
            best_qid = questions[0].get("id")
        if best_qid is None:
            continue

        q_dir = run_dir / best_qid
        q_dir.mkdir(parents=True, exist_ok=True)
        n = len(out.get(best_qid, []))
        filename = f"{n}{VALID_IMAGE_EXT}"
        file_path = q_dir / filename
        try:
            Image.fromarray(crop).save(file_path, format="PNG")
        except Exception as e:
            logger.warning("保存插图失败 %s: %s", file_path, e)
            continue
        if not _is_valid_image_file(file_path):
            try:
                file_path.unlink()
            except OSError:
                pass
            continue
        out.setdefault(best_qid, []).append(f"{url_prefix}/{best_qid}/{filename}")

    logger.info(
        "按题插图截取完成 run_id=%s 图块=%s 题目分配=%s",
        run_id,
        len(figure_boxes),
        {k: len(v) for k, v in out.items() if v},
    )
    return out
