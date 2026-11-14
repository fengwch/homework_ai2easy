"""
插图截取与校验逻辑的单元测试：后缀必须为 .png，内容校验通过才加入 figure_urls。
"""
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ocr.figures import (
    _get_figures_dir,
    _is_valid_image_file,
    extract_and_save_figures,
    VALID_IMAGE_EXT,
    MIN_FILE_SIZE_BYTES,
)
from ocr.preprocessing.image_preprocessing import preprocess_image

# 指定要测试的真实图片路径（可修改为其他图片）
ROOT_DIR = Path(__file__).resolve().parent.parent
# 默认使用幼儿园作业图，可改为其他图片，如：ROOT_DIR / "imgs" / "六年级.png"
TEST_IMAGE_PATH = ROOT_DIR / "imgs" / "六年级.png"


class TestValidImageFile:
    """_is_valid_image_file 后缀与内容校验。"""

    def test_rejects_non_png_suffix(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff" + b"\x00" * 200)
            path = Path(f.name)
        try:
            assert _is_valid_image_file(path) is False
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_missing_file(self):
        p = Path("/nonexistent/fig.png")
        assert p.suffix.lower() == ".png"
        assert _is_valid_image_file(p) is False

    def test_rejects_tiny_file(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"x" * (MIN_FILE_SIZE_BYTES - 1))
            path = Path(f.name)
        try:
            assert _is_valid_image_file(path) is False
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_all_white_image(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = Path(f.name)
        try:
            img = Image.new("RGB", (50, 50), (255, 255, 255))
            img.save(path, format="PNG")
            assert path.stat().st_size >= MIN_FILE_SIZE_BYTES
            assert _is_valid_image_file(path) is False
        finally:
            path.unlink(missing_ok=True)

    def test_accepts_valid_png_with_content(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = Path(f.name)
        try:
            img = Image.new("RGB", (50, 50), (255, 255, 255))
            arr = np.array(img)
            arr[10:40, 10:40] = [0, 0, 0]
            Image.fromarray(arr).save(path, format="PNG")
            assert _is_valid_image_file(path) is True
        finally:
            path.unlink(missing_ok=True)


def _has_cv2():
    try:
        import cv2  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.fixture(scope="module")
def test_image_path():
    """测试图片路径 fixture，图片不存在时跳过测试。"""
    if not TEST_IMAGE_PATH.exists():
        pytest.skip(f"测试图片不存在: {TEST_IMAGE_PATH}，请将图片放到该路径")
    return str(TEST_IMAGE_PATH)


@pytest.fixture(scope="module")
def test_image_array(test_image_path):
    """测试图片的预处理 numpy 数组。"""
    return preprocess_image(test_image_path)


class TestExtractAndSaveFigures:
    """extract_and_save_figures 只保存 .png 且仅返回通过校验的 URL。"""

    @pytest.mark.skipif(not _has_cv2(), reason="需要 opencv-python-headless")
    def test_returns_only_png_urls(self):
        """返回的 URL 必须以 .png 结尾。"""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        img[50:150, 50:150] = [30, 30, 30]
        urls = extract_and_save_figures(img, run_id="test_png_suffix")
        for u in urls:
            assert u.endswith(".png"), f"URL 应为 .png 后缀: {u}"
            assert u.count(".png") == 1

    @pytest.mark.skipif(not _has_cv2(), reason="需要 opencv-python-headless")
    def test_saved_paths_are_files_not_dirs(self):
        """保存的路径必须是文件，不能只是目录。"""
        img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        img[50:150, 50:150] = [30, 30, 30]
        run_id = "test_files_not_dirs"
        urls = extract_and_save_figures(img, run_id=run_id)
        figures_dir = _get_figures_dir()
        run_dir = figures_dir / run_id
        if urls:
            for u in urls:
                name = u.split("/")[-1]
                fp = run_dir / name
                assert fp.is_file(), f"应为文件而非目录: {fp}"
                assert fp.suffix.lower() == VALID_IMAGE_EXT
                assert fp.stat().st_size >= MIN_FILE_SIZE_BYTES

    @pytest.mark.skipif(not _has_cv2(), reason="需要 opencv-python-headless")
    def test_extract_figures_from_real_image(self, test_image_path, test_image_array):
        """
        使用真实图片（幼儿园-1.png）测试插图截取。
        修改文件顶部的 TEST_IMAGE_PATH 可切换为其他图片。
        """
        run_id = "test_real_image"
        urls = extract_and_save_figures(test_image_array, run_id=run_id)
        
        # 验证返回的 URL 都是 .png 后缀
        for u in urls:
            assert u.endswith(".png"), f"URL 应为 .png 后缀: {u}"
        
        # 验证保存的文件存在且有效
        figures_dir = _get_figures_dir()
        run_dir = figures_dir / run_id
        if urls:
            assert run_dir.exists(), f"应创建 run 目录: {run_dir}"
            for u in urls:
                name = u.split("/")[-1]
                fp = run_dir / name
                assert fp.is_file(), f"应为文件而非目录: {fp}"
                assert fp.suffix.lower() == VALID_IMAGE_EXT
                assert fp.stat().st_size >= MIN_FILE_SIZE_BYTES
                # 验证文件内容有效（通过校验函数）
                assert _is_valid_image_file(fp), f"保存的文件应通过校验: {fp}"
