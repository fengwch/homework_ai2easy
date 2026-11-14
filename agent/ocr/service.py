"""
OCR 服务入口：预处理 → 识别（百度 OCR / PaddleOCR）→ 后处理（题目解析）。
一张图片拆分为多道题目；题目中的答案提取并返回；明显插图截取保存并返回链接。
输出与前端 scan-status / 作业详情中 questions 一致。
"""
import base64
import io
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import yaml
from PIL import Image

from ocr.preprocessing.image_preprocessing import preprocess_image
from ocr.postprocessing.question_parser import parse_questions_from_text
from ocr.figures import extract_and_save_figures, extract_figures_for_questions
from utils.logging import get_logger

logger = get_logger(__name__)


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "configs" / "ocr_config.yaml"
    if not config_path.exists():
        cfg = {"engine": "baidu", "question_parsing": {"use_llm": False, "subject_hint": "数学"}}
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    # .env 中的 OCR_ENGINE 优先于 yaml（可选值: baidu | paddle | qwen_vl）
    env_engine = os.getenv("OCR_ENGINE")
    if env_engine and env_engine.strip():
        cfg["engine"] = env_engine.strip().lower()
    return cfg


def _raw_bytes_from_input(image_data: Union[bytes, str, Path]) -> bytes:
    """从 image_data 得到原始图片 bytes（不做预处理）。"""
    if isinstance(image_data, str):
        try:
            raw = base64.b64decode(image_data)
            if len(raw) > 0:
                return raw
        except Exception:
            pass
        path = Path(image_data)
        if path.exists():
            with open(image_data, "rb") as f:
                return f.read()
        raise ValueError("image_data 既非合法 base64，也不是存在的文件路径")
    if isinstance(image_data, bytes):
        return image_data
    with open(image_data, "rb") as f:
        return f.read()


def _image_to_bytes(image_data: Union[bytes, str, Path], preprocess: bool = True) -> bytes:
    """将 image_data（base64 字符串、bytes、或文件路径）转为用于 OCR 的图片 bytes。"""
    raw = _raw_bytes_from_input(image_data)
    if not preprocess:
        return raw
    arr = preprocess_image(raw)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _recognize_baidu(image_bytes: bytes, with_location: bool = False) -> Tuple[str, List[Dict[str, Any]]]:
    """
    返回 (full_text, ocr_lines)。
    ocr_lines 每项为 {"text": str, "box": (x,y,w,h) or None}，用于按题截插图。
    """
    from ocr.baidu_ocr import recognize, words_result_to_text, words_result_to_ocr_lines
    logger.debug("调用百度 OCR 识别 with_location=%s", with_location)
    result = recognize(image_bytes, with_location=with_location)
    text = words_result_to_text(result)
    ocr_lines = words_result_to_ocr_lines(result)
    return text, ocr_lines


def _recognize_paddle(image_bytes: bytes) -> str:
    try:
        import paddleocr
        import numpy as np
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        arr = np.array(img)
        ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, show_log=False)
        result = ocr.ocr(arr, cls=True)
        if not result or not result[0]:
            return ""
        lines = [line[1][0] for line in result[0]]
        return "\n".join(lines)
    except ImportError:
        raise RuntimeError("PaddleOCR 未安装，请安装 paddlepaddle 与 paddleocr，或在 configs/ocr_config.yaml 中设置 engine: baidu 并配置 BAIDU_OCR_API_KEY/SECRET_KEY")
    except Exception as e:
        raise RuntimeError(f"PaddleOCR 识别异常: {e}") from e


def _recognize_qwen_vl(image_bytes: bytes) -> str:
    """
    使用阿里云 DashScope Qwen-VL 多模态模型对图片做 OCR，提取全文并识别学科。
    需配置 DASHSCOPE_API_KEY；通过 .env 的 OCR_ENGINE=qwen_vl 或 yaml engine: qwen_vl 启用。
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("使用 Qwen-VL OCR 时请设置环境变量 DASHSCOPE_API_KEY")

    try:
        import dashscope
        from http import HTTPStatus
    except ImportError:
        raise RuntimeError("请安装 dashscope: pip install dashscope")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:image/png;base64,{image_b64}"
    prompt = (
        "请识别图片中的全部文字（包括数学公式、符号、题号等），并判断学科。"
        "输出格式：第一行 [学科] 数学/英语/语文 等，从下一行开始按原样输出所有识别到的文字，保持换行与顺序。"
    )
    messages = [
        {
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": prompt},
            ],
        }
    ]
    try:
        response = dashscope.MultiModalConversation.call(
            model="qwen-vl-plus",
            messages=messages,
            api_key=api_key,
        )
        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            if not content:
                return ""
            # DashScope 多模态返回 content 常为 list，如 [{"text": "..."}]
            if isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict) and "text" in c:
                        parts.append(c["text"])
                    elif isinstance(c, dict):
                        parts.append(str(c))
                    else:
                        parts.append(str(c))
                text = "\n".join(parts) if parts else ""
            elif isinstance(content, dict):
                text = content.get("text", str(content))
            else:
                text = str(content)
            # 去掉 [学科] xxx 前缀（若有），只保留正文给后续题目解析
            if "[学科]" in text or "学科]" in text:
                for sep in ("\n", " "):
                    if sep in text:
                        parts = text.split(sep, 1)
                        if len(parts) == 2 and ("学科" in parts[0] or "]" in parts[0]):
                            text = parts[1].strip()
                        break
            return text.strip() or ""
        raise RuntimeError(
            f"DashScope Qwen-VL OCR 调用失败: {getattr(response, 'code', response.status_code)} {getattr(response, 'message', '')}"
        )
    except Exception as e:
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        raise RuntimeError(f"Qwen-VL OCR 异常: {e}") from e


class OCRService:
    """OCR 服务：预处理、识别、题目解析，输出与前端一致的 questions。"""

    def __init__(self, config_path: str = None):
        self.config = _load_config() if config_path is None else self._load_path(config_path)

    @staticmethod
    def _load_path(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def recognize(
        self,
        image_data: Union[bytes, str, Path],
        subject: str = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        识别图片中的题目，返回 {"questions": [...]}，结构与前端 scan-status 完成时的 data.questions 一致。
        image_data: base64 字符串、图片 bytes、或本地文件路径。
        """
        logger.info("开始 OCR 识别", extra={"subject": subject, "engine": self.config.get("engine")})
        raw = _raw_bytes_from_input(image_data)
        img_array = preprocess_image(raw)
        buf = io.BytesIO()
        Image.fromarray(img_array).save(buf, format="PNG")
        image_bytes = buf.getvalue()

        engine = (self.config.get("engine") or "baidu").strip().lower()
        ocr_lines: List[Dict[str, Any]] = []
        if engine == "qwen_vl":
            full_text = _recognize_qwen_vl(image_bytes)
        elif engine == "paddle":
            try:
                full_text = _recognize_paddle(image_bytes)
            except RuntimeError as e:
                if "未安装" in str(e) or "PaddleOCR" in str(e):
                    logger.warning("PaddleOCR 未安装，回退到百度 OCR", exc_info=e)
                    full_text, ocr_lines = _recognize_baidu(image_bytes, with_location=True)
                else:
                    logger.error("PaddleOCR 识别异常", exc_info=e)
                    raise
        else:
            use_location = self.config.get("ocr_figures_use_location", True)
            full_text, ocr_lines = _recognize_baidu(image_bytes, with_location=use_location)

        qp = self.config.get("question_parsing") or {}
        subject = subject or qp.get("subject_hint") or "数学"
        ocr_line_texts = [line.get("text", "") for line in ocr_lines] if ocr_lines else None
        questions = parse_questions_from_text(
            full_text,
            subject=subject,
            use_llm=qp.get("use_llm", False),
            ocr_line_texts=ocr_line_texts,
        )

        figure_urls = []
        if self.config.get("ocr_figures_enabled", True):
            run_id = uuid.uuid4().hex[:12]
            has_boxes = any(line.get("box") for line in ocr_lines) if ocr_lines else False
            if has_boxes and ocr_lines:
                # 按题目、按「如图」截取，避开文字区域
                figure_by_q = extract_figures_for_questions(img_array, ocr_lines, questions, run_id=run_id)
                for q in questions:
                    qid = q.get("id", "")
                    meta = q.setdefault("metadata", {})
                    urls = figure_by_q.get(qid, [])
                    meta["figureUrls"] = urls
                    meta["hasImage"] = len(urls) > 0
                    figure_urls.extend(urls)
            else:
                # 无位置信息时退化为整图检测，均分到各题
                figure_urls = extract_and_save_figures(img_array, run_id=run_id)
                nq = max(1, len(questions))
                for i, q in enumerate(questions):
                    meta = q.setdefault("metadata", {})
                    start = (i * len(figure_urls)) // nq
                    end = ((i + 1) * len(figure_urls)) // nq
                    meta["figureUrls"] = figure_urls[start:end] if figure_urls else []
                    meta["hasImage"] = len(meta["figureUrls"]) > 0
        else:
            for q in questions:
                q.setdefault("metadata", {})["figureUrls"] = []
                q.setdefault("metadata", {})["hasImage"] = False

        logger.info(
            "OCR 题目解析完成",
            extra={"questions_count": len(questions), "figure_urls_count": len(figure_urls)},
        )
        return {"questions": questions, "figure_urls": figure_urls}
