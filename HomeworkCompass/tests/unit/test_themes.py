"""主题元信息与按主题选底图的最小测试。"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, "src")

try:
    from homework_compass.layout.themes import get_theme, get_themes, theme_for_interests
except ImportError:
    pytest.skip("themes 模块未实现", allow_module_level=True)


def test_ten_themes_each_with_base_file():
    themes = get_themes()
    assert len(themes) == 10
    for t in themes:
        assert t.base_file.endswith("_quest-map.png")
        assert t.cn
        assert t.accent.startswith("#")


def test_theme_for_interests_orders_by_match_then_default():
    ranked = theme_for_interests(["恐龙", "汽车", "太空"])
    assert ranked[0] == "dinosaur"
    assert "space" in ranked[:3]
    # 未匹配的按默认顺序排在后面
    assert ranked[-1] == "pixel"


def test_unknown_interest_ignored():
    ranked = theme_for_interests(["不存在的东西"])
    assert ranked[0] == "dinosaur"  # 默认第一


from homework_compass.layout.themes import skin_palette  # noqa: E402


def test_skin_palette_compat():
    assert skin_palette("dinosaur")["accent"] == "#3F7D3A"
    assert skin_palette("nope")["accent"].startswith("#")
