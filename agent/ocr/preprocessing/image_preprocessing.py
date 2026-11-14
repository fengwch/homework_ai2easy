"""
图像预处理：裁剪、旋转、亮度对比度调整等。
配置从 configs/ocr_config.yaml 的 enhancement 读取。
"""
import io
from pathlib import Path
from typing import Union

import yaml


def _load_enhancement_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent / "configs" / "ocr_config.yaml"
    if not config_path.exists():
        return {"enabled": False, "contrast": False, "brightness": False, "sharpen": False}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("enhancement") or {"enabled": False, "contrast": False, "brightness": False, "sharpen": False}


def _open_image(image_data: Union[bytes, str, Path]) -> "Image":
    from PIL import Image
    if isinstance(image_data, bytes):
        return Image.open(io.BytesIO(image_data)).convert("RGB")
    if isinstance(image_data, (str, Path)):
        path = Path(image_data)
        if path.exists():
            return Image.open(path).convert("RGB")
        # 可能是 URL，调用方需先下载为 bytes 再传入
        raise ValueError("image_data 为路径时该路径必须存在；URL 请先下载为 bytes 传入")
    raise TypeError("image_data 应为 bytes 或文件路径")


def preprocess_image(
    image_data: Union[bytes, str, Path],
    enhancement: dict = None,
) -> "np.ndarray":
    """
    预处理图像：打开、可选增强、转为 numpy 数组供 OCR 使用。
    """
    import numpy as np
    from PIL import ImageEnhance, ImageFilter, Image

    config = enhancement or _load_enhancement_config()
    image = _open_image(image_data)

    if config.get("enabled"):
        if config.get("contrast"):
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
        if config.get("brightness"):
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.2)
        if config.get("sharpen"):
            image = image.filter(ImageFilter.SHARPEN)

    return np.array(image)
