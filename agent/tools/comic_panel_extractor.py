#!/usr/bin/env python3
"""
Comic Panel Extractor Skill
专门用于按漫画实际镜头边框精确剪裁分镜头的工具
作者: OpenClaw Assistant
用途: 将漫画图片按真实分镜头边框分割成多个独立图片

本文件严格基于 /Users/fengwanchang/.openclaw/workspace/comic-panel-extractor.py 实现，
提供相同的函数行为，用于在项目中按文件路径输入进行分格剪裁。
"""

import argparse
import os
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np


def extract_comic_panels_by_borders(
    input_path: str,
    output_dir: str,
    target_count: Optional[int] = None,
) -> List[Tuple[str, Tuple[int, int]]]:
    """
    按漫画实际镜头边框精确剪裁分镜头

    Args:
        input_path: 输入漫画图片路径
        output_dir: 输出目录
        target_count: 目标分镜头数量（可选）

    Returns:
        列表 [(输出文件路径, (宽, 高)), ...]
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 读取图片
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"无法读取图片: {input_path}")

    height, width = img.shape[:2]
    print(f"原始图像尺寸: {width}x{height}")

    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 高斯模糊减少噪声
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny 边缘检测
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    # 膨胀操作连接边缘
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)

    # 查找轮廓
    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # 过滤和排序轮廓（带异常小分镜检测与重试逻辑）
    def _filter_contours(min_area: int, min_w: int, min_h: int) -> list[tuple[int, int, int, int]]:
        out: list[tuple[int, int, int, int]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            # 过滤掉太小的区域（可能是噪声）
            if area > min_area and w > min_w and h > min_h:
                # 排除接近整个图像的轮廓（可能是外边框）
                if not (w > width * 0.95 and h > height * 0.95):
                    out.append((x, y, w, h))
        return out

    # 第一次按较宽松阈值过滤
    valid_contours: list[tuple[int, int, int, int]] = _filter_contours(min_area=1000, min_w=50, min_h=50)

    # 如果一个分镜特别小（长宽和面积都远小于整图），认为边框检测可能异常
    def _has_tiny_panel(rects: list[tuple[int, int, int, int]]) -> bool:
        if not rects:
            return False
        img_area = width * height
        tiny_w = max(40, int(width * 0.08))
        tiny_h = max(40, int(height * 0.08))
        tiny_area = max(2000, int(img_area * 0.015))
        for _, _, w, h in rects:
            area = w * h
            if (w < tiny_w and h < tiny_h) or area < tiny_area:
                return True
        return False

    # 若检测到异常小分镜，尝试用更严格的阈值重跑一次边框过滤
    if _has_tiny_panel(valid_contours):
        print("检测到异常小的分镜，重新执行一次边框检测以排除噪声分格...")
        valid_contours = _filter_contours(
            min_area=5000,
            min_w=max(80, int(width * 0.1)),
            min_h=max(80, int(height * 0.1)),
        )

    # 如果仍然没有有效轮廓，或仍存在异常小分镜，则启动备用网格分割
    if len(valid_contours) == 0 or _has_tiny_panel(valid_contours):
        print("边框检测结果不稳定，启动备用网格分割...")
        return extract_by_grid(img, output_dir, target_count or 11)

    # 根据目标数量调整（此处只提示，不强制）
    if target_count and len(valid_contours) != target_count:
        print(f"检测到 {len(valid_contours)} 个分镜头，但目标是 {target_count} 个")
        # 如需更精细控制，可在此处增加合并/拆分逻辑

    # 按位置排序（从上到下，从左到右）
    valid_contours.sort(key=lambda rect: (rect[1], rect[0]))

    # 保存每个分镜头
    panels: list[Tuple[str, Tuple[int, int]]] = []
    use_contours = (
        valid_contours[:target_count] if target_count else valid_contours
    )
    for i, (x, y, w, h) in enumerate(use_contours):
        panel = img[y : y + h, x : x + w]
        output_path = os.path.join(output_dir, f"panel_{i + 1:02d}.jpg")
        cv2.imwrite(output_path, panel)
        panels.append((output_path, (w, h)))
        print(f"保存分镜头 {i + 1}: {output_path} ({w}x{h})")

    print(f"总共提取了 {len(panels)} 个分镜头")
    return panels


def extract_by_grid(
    img,
    output_dir: str,
    count: int = 11,
) -> List[Tuple[str, Tuple[int, int]]]:
    """备用网格分割方法"""
    height, width = img.shape[:2]

    # 根据常见漫画布局进行分割
    if count == 11:
        # 假设是 2-3-3-3 的布局
        panels: list[tuple[int, int, int, int]] = []

        # 第一行：2 个大面板
        row_height = height // 4
        panels.append((0, 0, width // 2, row_height))
        panels.append((width // 2, 0, width // 2, row_height))

        # 第二行：3 个小面板
        panels.append((0, row_height, width // 3, row_height))
        panels.append((width // 3, row_height, width // 3, row_height))
        panels.append((2 * width // 3, row_height, width // 3, row_height))

        # 第三行：3 个小面板
        panels.append((0, 2 * row_height, width // 3, row_height))
        panels.append((width // 3, 2 * row_height, width // 3, row_height))
        panels.append((2 * width // 3, 2 * row_height, width // 3, row_height))

        # 第四行：3 个小面板
        panels.append(
            (0, 3 * row_height, width // 3, height - 3 * row_height)
        )
        panels.append(
            (width // 3, 3 * row_height, width // 3, height - 3 * row_height)
        )
        panels.append(
            (2 * width // 3, 3 * row_height, width // 3, height - 3 * row_height)
        )

        # 保存面板
        saved_panels: list[Tuple[str, Tuple[int, int]]] = []
        for i, (x, y, w, h) in enumerate(panels[:count]):
            panel = img[y : y + h, x : x + w]
            output_path = os.path.join(output_dir, f"panel_{i + 1:02d}.jpg")
            cv2.imwrite(output_path, panel)
            saved_panels.append((output_path, (w, h)))
            print(f"保存分镜头 {i + 1}: {output_path} ({w}x{h})")

        print(f"总共提取了 {len(saved_panels)} 个分镜头（网格模式）")
        return saved_panels

    # 常见规则网格布局：3x4, 3x5, 3x6, 4x4, 4x5
    grid_map: dict[int, tuple[int, int]] = {
        12: (3, 4),  # 3 行 4 列
        15: (3, 5),  # 3 行 5 列
        18: (3, 6),  # 3 行 6 列
        16: (4, 4),  # 4 行 4 列
        20: (4, 5),  # 4 行 5 列
    }
    if count in grid_map:
        rows, cols = grid_map[count]
        panels: list[tuple[int, int, int, int]] = []
        cell_h = height // rows
        cell_w = width // cols
        for r in range(rows):
            for c in range(cols):
                x = c * cell_w
                y = r * cell_h
                # 最后一行/列吃掉余数，避免底部/右侧出现像素缝隙
                w = cell_w if c < cols - 1 else width - x
                h = cell_h if r < rows - 1 else height - y
                panels.append((x, y, w, h))

        saved_panels: list[Tuple[str, Tuple[int, int]]] = []
        for i, (x, y, w, h) in enumerate(panels[:count]):
            panel = img[y : y + h, x : x + w]
            output_path = os.path.join(output_dir, f"panel_{i + 1:02d}.jpg")
            cv2.imwrite(output_path, panel)
            saved_panels.append((output_path, (w, h)))
            print(f"保存分镜头 {i + 1}: {output_path} ({w}x{h})")

        print(f"总共提取了 {len(saved_panels)} 个分镜头（规则网格 {rows}x{cols}）")
        return saved_panels

    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="漫画分镜头精确提取工具")
    parser.add_argument("input", help="输入漫画图片路径")
    parser.add_argument("output", help="输出目录")
    parser.add_argument("--count", type=int, help="目标分镜头数量")

    args = parser.parse_args()
    extract_comic_panels_by_borders(args.input, args.output, args.count)


if __name__ == "__main__":
    main()

"""
漫画分格提取：从单张漫画/连环画图中检测分格边界，按格裁剪并返回每张剪切好的图片（base64）。
本地调用 extract_comic_panels(image_base64)；Coze 插件入口为 handler(args)。
"""
import base64
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np


class ComicPanelExtractor:
    def __init__(self, min_panel_area: int = 1000, max_panels: int = 20):
        self.min_panel_area = max(100, int(min_panel_area))
        self.max_panels = max(1, int(max_panels))

    def detect_panels_adaptive(self, image: np.ndarray) -> List[Dict[str, Any]]:
        original_height, original_width = image.shape[:2]

        scale = min(1.0, 800 / max(original_height, original_width))
        if scale < 1.0:
            resized = cv2.resize(
                image,
                (int(original_width * scale), int(original_height * scale)),
            )
        else:
            resized = image.copy()

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        panels_v1 = self._detect_by_contours(gray, resized, scale)
        panels_v2 = self._detect_by_lines(gray, resized, scale)
        panels_v3 = self._detect_grid_layout(gray, resized, scale)

        all_panels = panels_v1 + panels_v2 + panels_v3
        merged_panels = self._merge_overlapping_panels(all_panels)
        filtered_panels = self._filter_and_sort_panels(
            merged_panels, original_width, original_height
        )

        return filtered_panels[: self.max_panels]

    def _detect_by_contours(
        self, gray: np.ndarray, image: np.ndarray, scale: float
    ) -> List[Dict[str, Any]]:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        panels = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_panel_area * (scale**2):
                x, y, w, h = cv2.boundingRect(contour)
                panels.append(
                    {
                        "x": int(x / scale),
                        "y": int(y / scale),
                        "width": int(w / scale),
                        "height": int(h / scale),
                        "confidence": float(min(area / 10000, 1.0)),
                    }
                )
        return panels

    def _detect_by_lines(
        self, gray: np.ndarray, image: np.ndarray, scale: float
    ) -> List[Dict[str, Any]]:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
        )

        if lines is None:
            return []

        horizontal_lines: List[Tuple[int, int, int, int]] = []
        vertical_lines: List[Tuple[int, int, int, int]] = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < abs(x2 - x1):
                horizontal_lines.append((x1, y1, x2, y2))
            else:
                vertical_lines.append((x1, y1, x2, y2))

        return self._create_panels_from_lines(
            horizontal_lines, vertical_lines, image.shape[1], image.shape[0], scale
        )

    def _detect_grid_layout(
        self, gray: np.ndarray, image: np.ndarray, scale: float
    ) -> List[Dict[str, Any]]:
        height, width = gray.shape
        panels: List[Dict[str, Any]] = []
        layouts = [(2, 2), (2, 3), (3, 2), (3, 3), (1, 2), (2, 1), (1, 3), (3, 1)]

        for rows, cols in layouts:
            panel_width = width // cols
            panel_height = height // rows

            for i in range(rows):
                for j in range(cols):
                    x = j * panel_width
                    y = i * panel_height
                    w = panel_width if j < cols - 1 else width - x
                    h = panel_height if i < rows - 1 else height - y

                    if w * h > self.min_panel_area * (scale**2):
                        panels.append(
                            {
                                "x": int(x / scale),
                                "y": int(y / scale),
                                "width": int(w / scale),
                                "height": int(h / scale),
                                "confidence": 0.7,
                            }
                        )
        return panels

    def _create_panels_from_lines(
        self,
        horizontal_lines: List[Tuple[int, int, int, int]],
        vertical_lines: List[Tuple[int, int, int, int]],
        width: int,
        height: int,
        scale: float,
    ) -> List[Dict[str, Any]]:
        if not horizontal_lines or not vertical_lines:
            return []

        y_coords: set = set()
        x_coords: set = set()

        for x1, y1, x2, y2 in horizontal_lines:
            y_coords.add(y1)
            y_coords.add(y2)

        for x1, y1, x2, y2 in vertical_lines:
            x_coords.add(x1)
            x_coords.add(x2)

        y_coords.update([0, height])
        x_coords.update([0, width])

        y_list = sorted(list(y_coords))
        x_list = sorted(list(x_coords))

        panels = []
        for i in range(len(y_list) - 1):
            for j in range(len(x_list) - 1):
                x = x_list[j]
                y = y_list[i]
                w = x_list[j + 1] - x
                h = y_list[i + 1] - y

                if w * h > self.min_panel_area * (scale**2):
                    panels.append(
                        {
                            "x": int(x / scale),
                            "y": int(y / scale),
                            "width": int(w / scale),
                            "height": int(h / scale),
                            "confidence": 0.8,
                        }
                    )
        return panels

    def _merge_overlapping_panels(
        self, panels: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if len(panels) <= 1:
            return panels

        merged: List[Dict[str, Any]] = []
        used = [False] * len(panels)

        for i, panel1 in enumerate(panels):
            if used[i]:
                continue

            current = panel1.copy()
            used[i] = True

            for j, panel2 in enumerate(panels):
                if used[j]:
                    continue

                overlap = self._calculate_overlap(current, panel2)
                if overlap > 0.3:
                    x1 = min(current["x"], panel2["x"])
                    y1 = min(current["y"], panel2["y"])
                    x2 = max(
                        current["x"] + current["width"],
                        panel2["x"] + panel2["width"],
                    )
                    y2 = max(
                        current["y"] + current["height"],
                        panel2["y"] + panel2["height"],
                    )

                    current = {
                        "x": x1,
                        "y": y1,
                        "width": x2 - x1,
                        "height": y2 - y1,
                        "confidence": max(
                            current["confidence"], panel2["confidence"]
                        ),
                    }
                    used[j] = True

            merged.append(current)

        return merged

    def _calculate_overlap(self, panel1: Dict, panel2: Dict) -> float:
        x1 = max(panel1["x"], panel2["x"])
        y1 = max(panel1["y"], panel2["y"])
        x2 = min(
            panel1["x"] + panel1["width"],
            panel2["x"] + panel2["width"],
        )
        y2 = min(
            panel1["y"] + panel1["height"],
            panel2["y"] + panel2["height"],
        )

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = (
            panel1["width"] * panel1["height"]
            + panel2["width"] * panel2["height"]
            - intersection
        )
        return float(intersection / union) if union > 0 else 0.0

    def _filter_and_sort_panels(
        self,
        panels: List[Dict[str, Any]],
        image_width: int,
        image_height: int,
    ) -> List[Dict[str, Any]]:
        filtered = []
        for panel in panels:
            area = panel["width"] * panel["height"]
            if (
                area > self.min_panel_area
                and area < image_width * image_height * 0.9
                and panel["width"] > 20
                and panel["height"] > 20
            ):
                filtered.append(panel)

        filtered.sort(
            key=lambda p: (p["y"] + p["height"] // 2, p["x"] + p["width"] // 2)
        )
        return filtered


def _decode_image_from_base64(image_data: str) -> np.ndarray:
    if not image_data or not isinstance(image_data, str):
        raise ValueError("image 不能为空，且必须是 base64 字符串")

    if image_data.startswith("data:image"):
        image_data = image_data.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(image_data)
    except Exception as e:
        raise ValueError(f"base64 解码失败: {e}") from e

    image = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR
    )
    if image is None:
        raise ValueError("无法解码图像，请确认是有效图片的 base64")
    return image


def _crop_panels_to_base64(
    image: np.ndarray, panels: List[Dict[str, Any]], format: str = "png"
) -> List[str]:
    """按 panels 坐标裁剪 image，返回每格图片的 base64 列表（与 panels 顺序一致）。"""
    ext = ".png" if format.lower() == "png" else ".jpg"
    encode_param = [cv2.IMWRITE_PNG_COMPRESSION, 6] if ext == ".png" else [cv2.IMWRITE_JPEG_QUALITY, 90]
    out = []
    h_total, w_total = image.shape[:2]
    for p in panels:
        x = max(0, int(p["x"]))
        y = max(0, int(p["y"]))
        w = int(p["width"])
        h = int(p["height"])
        # 边界裁剪，避免越界
        x2 = min(x + w, w_total)
        y2 = min(y + h, h_total)
        if x2 <= x or y2 <= y:
            continue
        crop = image[y:y2, x:x2]
        _, buf = cv2.imencode(ext, crop, encode_param)
        if buf is not None:
            out.append(base64.b64encode(buf.tobytes()).decode("utf-8"))
    return out


def extract_comic_panels(
    image_data: str,
    min_panel_area: int = 1000,
    max_panels: int = 20,
    return_crops: bool = True,
    crop_format: str = "png",
) -> Dict[str, Any]:
    """
    从 base64 图片中提取漫画分格，并直接返回剪切好的每格图片（base64）。

    Args:
        image_data: Base64 编码的图片（可含 data:image/...;base64, 前缀）
        min_panel_area: 最小面板面积（像素²）
        max_panels: 最多返回的面板数量
        return_crops: 是否返回每格裁剪后的图片 base64 列表，默认 True
        crop_format: 裁剪图编码格式，"png" 或 "jpg"

    Returns:
        {
            "success": bool,
            "panel_count": int,
            "panels": [{"x", "y", "width", "height", "confidence"}, ...],
            "panel_images": [base64_str, ...]  与 panels 一一对应，仅当 return_crops=True
            "error": str (仅当 success=False),
            "message": str,
        }
    """
    try:
        image = _decode_image_from_base64(image_data)
        extractor = ComicPanelExtractor(
            min_panel_area=min_panel_area,
            max_panels=max_panels,
        )
        panels = extractor.detect_panels_adaptive(image)

        result: Dict[str, Any] = {
            "success": True,
            "panel_count": len(panels),
            "panels": panels,
            "message": "ok",
        }
        if return_crops and panels:
            result["panel_images"] = _crop_panels_to_base64(
                image, panels, format=crop_format
            )
        else:
            result["panel_images"] = []

        return result
    except Exception as e:
        return {
            "success": False,
            "panel_count": 0,
            "panels": [],
            "panel_images": [],
            "error": str(e),
            "message": "failed",
        }


def _get_input_value(inp: Any, key: str, default: Any = None) -> Any:
    if inp is None:
        return default
    if isinstance(inp, dict):
        return inp.get(key, default)
    try:
        val = getattr(inp, key, default)
        if val is not None:
            return val
    except Exception:
        pass
    try:
        return inp.get(key, default)
    except Exception:
        return default


def _image_input_to_bytes(image_data: str) -> bytes:
    """
    将 image 入参转为图片字节：支持 URL（http/https）或 base64 字符串（可含 data:image 前缀）。
    """
    if not image_data or not isinstance(image_data, str):
        raise ValueError("image 不能为空，且必须是字符串（URL 或 base64）")
    s = image_data.strip()
    if s.startswith("http://") or s.startswith("https://"):
        import urllib.request
        import urllib.error
        import ssl
        # 方案一：在当前工具内部关闭证书校验（仅适用于内网/测试环境）
        # 创建一个不校验证书的 SSL 上下文，后续所有 urlopen 调用都复用
        ctx = ssl._create_unverified_context()
        try:
            # 优先按原始 URL（可能是 https）尝试
            with urllib.request.urlopen(s, timeout=30, context=ctx) as resp:
                return resp.read()
        except Exception as e:
            # 若服务端通过 302 等 3xx 做跳转，且未被自动处理，则手动读取 Location 重新请求一次
            if isinstance(e, urllib.error.HTTPError) and 300 <= e.code < 400:
                redirect_url = e.headers.get("Location")
                if redirect_url:
                    s = redirect_url.strip()
                    try:
                        with urllib.request.urlopen(s, timeout=30, context=ctx) as resp:
                            return resp.read()
                    except Exception as e_redirect:
                        # 若重定向后的 URL 仍失败，则把异常继续交给后续 https→http 兜底逻辑处理
                        e = e_redirect
            # 若是 https 访问失败，尝试自动回退为 http 再请求一次
            if s.startswith("https://"):
                fallback = "http://" + s[len("https://") :]
                try:
                    with urllib.request.urlopen(fallback, timeout=30, context=ctx) as resp:
                        return resp.read()
                except Exception as e2:
                    raise ValueError(
                        f"图片 URL 拉取失败（https 与 http 均失败）: {e2}"
                    ) from e2
            raise ValueError(f"图片 URL 拉取失败: {e}") from e
    # base64
    data_str = s
    if data_str.startswith("data:image"):
        data_str = data_str.split(",", 1)[1]
    try:
        return base64.b64decode(data_str)
    except Exception as e:
        raise ValueError(f"image base64 解码失败: {e}") from e


def _detect_panels_by_borders_image(
    img: np.ndarray,
    target_count: Optional[int] = None,
) -> List[Tuple[int, int, int, int]]:
    """
    纯内存版的边框检测：不依赖文件读写，返回 (x, y, w, h) 列表。
    逻辑与 extract_comic_panels_by_borders 基本一致。
    """
    if img is None:
        raise ValueError("输入图像为空")

    height, width = img.shape[:2]

    # 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 高斯模糊
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Canny 边缘
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
    # 膨胀连接边缘
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    # 查找轮廓
    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # 过滤轮廓
    valid_contours: List[Tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area > 1000 and w > 50 and h > 50:
            # 排除接近整幅的外边框
            if not (w > width * 0.95 and h > height * 0.95):
                valid_contours.append((x, y, w, h))

    # 若无有效轮廓，则回退为整图一个 panel
    if not valid_contours:
        return [(0, 0, width, height)]

    # 按位置排序（从上到下，从左到右）
    valid_contours.sort(key=lambda rect: (rect[1], rect[0]))

    if target_count:
        return valid_contours[:target_count]
    return valid_contours


def handler(args: Any) -> Dict[str, Any]:
    """
    Coze 插件入口（纯内存实现，不依赖系统文件与目录写操作）。

    使用 _detect_panels_by_borders_image（基于 Canny + 轮廓）在内存中完成实际分格检测，
    直接返回每个分格的 data:image/png;base64,XXX 字符串。

    Input:
      - image: str，必填。支持两种形式：
          1）整页漫画的 base64（可带 data:image/...;base64, 前缀）；
          2）图片 URL（http:// 或 https://）。
      - max_panels: int，可选，期望最大分镜数量（映射到 target_count）

    Output:
      - success: bool
      - panel_count: int
      - panels: [{ \"index\": int, \"x\": int, \"y\": int, \"width\": int, \"height\": int }, ...]
      - panel_images: [data:image/png;base64,XXX, ...]
      - message: "ok" | "failed"
      - error: str（仅当 failed 时存在）
    """
    logger = getattr(args, "logger", None)
    if logger:
        logger.info("开始漫画分格检测并裁剪（border-based, in-memory）")

    try:
        inp = getattr(args, "input", args)
        image_data = _get_input_value(inp, "image", "")
        max_panels = _get_input_value(inp, "max_panels", None)

        # URL 或 base64 → bytes
        raw_bytes = _image_input_to_bytes(image_data or "")
        # bytes → np.ndarray
        img_array = cv2.imdecode(
            np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR
        )
        if img_array is None:
            raise ValueError("无法从提供的 image 解码出有效图片")

        target_count = (
            int(max_panels) if max_panels not in (None, "", 0) else None
        )

        # 纯内存边框检测
        borders = _detect_panels_by_borders_image(
            img_array,
            target_count=target_count,
        )

        panel_images: List[str] = []
        panel_infos: List[Dict[str, Any]] = []
        # 内存中裁剪，并编码为 data:image/png;base64,XXX
        for i, (x, y, w, h) in enumerate(borders):
            x, y, w, h = int(x), int(y), int(w), int(h)
            if w <= 0 or h <= 0:
                continue
            crop = img_array[y : y + h, x : x + w]
            if crop.size == 0:
                continue
            ok, buf = cv2.imencode(".png", crop)
            if not ok or buf is None:
                continue
            b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
            data_url = f"data:image/png;base64,{b64}"
            panel_images.append(data_url)
            panel_infos.append(
                {
                    "index": i,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                }
            )

        result: Dict[str, Any] = {
            "success": True,
            "panel_count": int(len(panel_infos)),
            "panels": panel_infos,
            "panel_images": panel_images,
            "message": "ok",
            "error": "",
        }
        if logger:
            for k, v in result.items():
                if k == "panel_images" and isinstance(v, list):
                    logger.info("  %s: list[len=%s]", k, len(v))
                    for i, b64 in enumerate(v):
                        head = (b64[:60] + "…") if len(b64) > 60 else b64
                        logger.info("    [%s] %s", i, head)
                else:
                    logger.info("  %s: %s", k, v)
            logger.info(
                "分格检测完成（border-based, in-memory）: count=%s",
                result["panel_count"],
            )
        return result
    except Exception as e:
        if logger:
            logger.error("漫画分格检测异常（border-based, in-memory）: %s", e)
        return {
            "success": False,
            "panel_count": 0,
            "panels": [],
            "panel_images": [],
            "message": "failed",
            "error": str(e),
        }
