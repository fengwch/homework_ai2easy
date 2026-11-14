"""
漫画分格提取工具单元测试：
- 使用 imgs/story/2026030801/story.png，验证按原始脚本的文件路径接口切分并输出到 childs 目录；
- 使用 tests/base64.txt 中的 base64，验证 handler 的入参与返回，并将裁剪图保存到 tests/base64_childs。
"""
import base64
from pathlib import Path
from typing import Optional

import pytest

from tools.comic_panel_extractor import (
    extract_comic_panels_by_borders,
    handler,
)


class TestExtractComicPanelsByBorders:
    """基于 /Users/fengwanchang/.openclaw/workspace/comic-panel-extractor.py 的行为测试。"""

    def test_story_image_extracts_panels_to_childs(self):
        """直接读取 story.png，调用 extract_comic_panels_by_borders，并将结果输出到项目根目录 childs。"""
        root = Path(__file__).resolve().parent.parent
        #
        input_path = root / "imgs" / "story" / "2026091001" / "story.png"
        assert input_path.exists(), f"测试图片不存在: {input_path}"

        output_dir = root / "imgs" / "story" / "2026091001"  / "childs"
        panels = extract_comic_panels_by_borders(str(input_path), str(output_dir))

        # 打印所有返回结果，方便人工核对
        print("\n--- extract_comic_panels_by_borders 返回 panels ---")
        for i, (out_path, (w, h)) in enumerate(panels, start=1):
            print(f"  {i:02d}: {out_path} ({w}x{h})")
        print(f"总共提取 {len(panels)} 个分镜头，输出目录: {output_dir}\n")

        # 断言基本行为
        assert len(panels) >= 1
        for out_path, (w, h) in panels:
            p = Path(out_path)
            assert p.exists()
            assert p.is_file()
            assert w > 0 and h > 0

    @pytest.mark.parametrize("target_count", [None, 11])
    def test_story_image_with_target_count(self, target_count: Optional[int]):
        """带 target_count 时，函数仍能正常执行（若检测数不一致，仅提示信息）。"""
        root = Path(__file__).resolve().parent.parent
        input_path = root / "imgs" / "story" / "2026091001" / "story.png"
        output_dir = root / "imgs" / "story" / "2026030801" / "childs_1"

        panels = extract_comic_panels_by_borders(
            str(input_path),
            str(output_dir),
            target_count=target_count,
        )
        assert len(panels) >= 1


class TestHandlerWithBase64File:
    """使用 tests/base64.txt 中的 base64 作为 image 入参，调用 handler。"""

    def test_handler_with_base64_txt(self):
        root = Path(__file__).resolve().parent.parent
        b64_file = root / "tests" / "base64.txt"
        assert b64_file.exists(), f"base64 测试文件不存在: {b64_file}"

        image_data = b64_file.read_text(encoding="utf-8").strip()
        assert image_data, "base64 内容不能为空"

        # 先将 base64 解码保存为图片，便于人工核对是否与原图一致
        raw_dir = root / "imgs" / "story" / "2026091001"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_out = raw_dir / "base64_raw.png"
        # 支持 data:image 前缀
        data_str = image_data
        if data_str.startswith("data:image"):
            data_str = data_str.split(",", 1)[1]
        raw_bytes = base64.b64decode(data_str)
        with open(raw_out, "wb") as f:
            f.write(raw_bytes)
        print(f"保存 base64 解码原图到: {raw_out}")

        class FakeArgs:
            input = {
                "image": image_data,
                # 其余参数可用默认值
            }
            logger = None

        out = handler(FakeArgs())

        # 打印结果概要，便于在终端查看
        print("\n--- handler(base64.txt) 返回 ---")
        print(f"success: {out.get('success')}")
        print(f"panel_count: {out.get('panel_count')}")
        print(f"keys: {list(out.keys())}")
        if isinstance(out.get("panel_images"), list):
            print(f"panel_images len: {len(out['panel_images'])}")
        print("--- end ---\n")

        # 将 panel_images 保存到 base64_childs 子目录，便于查看切剪效果
        childs_dir = root / "imgs" / "story" / "2026091001" / "base64_childs"
        childs_dir.mkdir(parents=True, exist_ok=True)
        for i, img_b64 in enumerate(out.get("panel_images", [])):
            data_str = img_b64 or ""
            # 兼容 data:image/...;base64,XXX 前缀
            if isinstance(data_str, str) and data_str.startswith("data:image"):
                data_str = data_str.split(",", 1)[1]
            raw = base64.b64decode(data_str)
            out_path = childs_dir / f"panel_{i:02d}.png"
            with open(out_path, "wb") as f:
                f.write(raw)
            print(f"  saved: {out_path}")
        print(f"  total {len(out.get('panel_images', []))} panels -> {childs_dir}\n")

        assert out.get("success") is True
        assert out.get("panel_count", 0) >= 1
