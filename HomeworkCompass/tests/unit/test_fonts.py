import sys
from pathlib import Path

import pytest
from PIL import ImageFont

from homework_compass.errors import FontError
from homework_compass.layout.fonts import (
    check_glyph_coverage, clear_cache, load_font, resolve_font_path,
)

pytestmark = pytest.mark.skipif(sys.platform != "darwin",
                                reason="候选表是 macOS 系统字体路径")

ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def test_resolve_finds_a_real_cjk_font():
    p = resolve_font_path()
    assert p and Path(p).is_file()


def test_loaded_font_is_at_least_requested_size():
    f = load_font(50)
    assert f.size == 50


def test_probe_passes_on_real_chinese():
    check_glyph_coverage(load_font(60))          # 不抛就是通过


def test_probe_rejects_font_without_the_sample_glyph():
    """豆腐块/空白必须被抓出来：poc 靠回退链碰运气，本机 PingFang 已不存在。"""
    fake = ImageFont.truetype(ARIAL, 60)
    with pytest.raises(FontError, match="字形覆盖"):
        check_glyph_coverage(fake)


def test_all_candidates_missing_raises_with_tried_paths(monkeypatch):
    from homework_compass.layout import fonts
    monkeypatch.setattr(fonts.Path, "is_file", lambda self: False)
    with pytest.raises(FontError, match="已尝试"):
        resolve_font_path(["/nonexistent/x.ttf"])


def test_cache_is_per_size_and_can_be_cleared():
    clear_cache()
    a, b = load_font(40), load_font(40)
    assert a is b
    clear_cache()
    assert load_font(40) is not a


def test_resolve_skips_existing_font_without_cjk():
    """路径存在不代表能画中文：Arial 存在但缺汉字，必须跳过而不是选中后炸掉。"""
    assert resolve_font_path([ARIAL, CJK]) == CJK


def test_only_bad_candidates_list_each_reason():
    with pytest.raises(FontError, match="字形覆盖"):
        resolve_font_path([ARIAL])


def test_hw_font_env_takes_priority(monkeypatch):
    """HW_FONT 指定随包字体时应排在系统路径之前——部署到没装中文字体的机器靠它。"""
    from homework_compass.layout import fonts as f
    f.clear_cache()
    found = f.resolve_font_path()
    monkeypatch.setenv("HW_FONT", found)
    # 把系统候选全换成不存在的路径：只有 HW_FONT 能用
    monkeypatch.setattr(f, "DEFAULT_CANDIDATES", ["/nope/a.ttc", "/nope/b.ttc"])
    f.clear_cache()
    try:
        assert f.resolve_font_path() == found
    finally:
        f.clear_cache()


def test_invalid_hw_font_falls_back(monkeypatch):
    """HW_FONT 指向不存在或非字体的文件时不能崩，要继续回退。"""
    from homework_compass.layout import fonts as f
    f.clear_cache()
    ok = f.resolve_font_path()
    monkeypatch.setenv("HW_FONT", "/nope/missing.ttc")
    monkeypatch.setattr(f, "DEFAULT_CANDIDATES", [ok])
    f.clear_cache()
    try:
        assert f.resolve_font_path() == ok
    finally:
        f.clear_cache()
