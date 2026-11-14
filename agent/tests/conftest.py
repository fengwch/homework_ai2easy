"""
Pytest 公共 fixture：本地测试图片路径与 base64。
使用 imgs/数学题目-1.jpg 作为 OCR 单元测试与接口测试的输入。
"""
import base64
from pathlib import Path

import logging
import pytest
# 在加载 .env 前抑制 dotenv 解析单行失败时的 stderr 警告
for _n in ("dotenv", "dotenv.main"):
    logging.getLogger(_n).setLevel(logging.ERROR)
from utils.env import safe_load_dotenv

# 项目根目录（agent），并在此加载 .env，保证 pytest 运行时能读到 BAIDU_OCR_*、DASHSCOPE_API_KEY 等
ROOT_DIR = Path(__file__).resolve().parent.parent
safe_load_dotenv(ROOT_DIR / ".env")
# SAMPLE_IMAGE_PATH = ROOT_DIR / "imgs" / "数学题目-2.jpg"
SAMPLE_IMAGE_PATH = ROOT_DIR / "imgs" / "小学四年级数学试题.png"
# 漫画分格测试用：12 格连环画 story.png
STORY_COMIC_IMAGE_PATH = ROOT_DIR / "imgs" / "story" / "2026030801" / "story.png"


@pytest.fixture(scope="session")
def story_comic_image_path():
    """漫画分格测试用图片路径（imgs/story/2026030801/story.png）。"""
    assert STORY_COMIC_IMAGE_PATH.exists(), f"测试图片不存在: {STORY_COMIC_IMAGE_PATH}"
    return str(STORY_COMIC_IMAGE_PATH)


@pytest.fixture(scope="session")
def story_comic_image_base64(story_comic_image_path):
    """同一张漫画图的 base64，供分格提取测试使用。"""
    with open(story_comic_image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


@pytest.fixture(scope="session")
def sample_image_path():
    """本地数学题目图片路径（imgs/数学题目-1.jpg）。"""
    assert SAMPLE_IMAGE_PATH.exists(), f"测试图片不存在: {SAMPLE_IMAGE_PATH}"
    return str(SAMPLE_IMAGE_PATH)


@pytest.fixture(scope="session")
def sample_image_base64(sample_image_path):
    """同一张图片的 base64 编码，供接口测试使用。"""
    with open(sample_image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


@pytest.fixture(scope="session")
def sample_image_bytes(sample_image_path):
    """同一张图片的原始 bytes。"""
    with open(sample_image_path, "rb") as f:
        return f.read()
