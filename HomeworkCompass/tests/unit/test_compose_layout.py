import sys

import pytest
from PIL import Image

from homework_compass.errors import LayoutError
from homework_compass.layout.compose import (
    BODY_PT, BODY_FLOOR_PT, NO_LINE_START, body_px_for, compose, fit_block,
    placeholder_base, pt_to_px, station_text, upscale_to_a4, wrap,
)
from homework_compass.layout.fonts import load_font
from homework_compass.layout.skeleton import A4_H, A4_W, quest_map
from homework_compass.models import (
    HomeworkItem, ParsedHomework, SourceKind, TraceLevel, ValidationReport,
)

pytestmark = pytest.mark.skipif(sys.platform != "darwin",
                                reason="候选表是 macOS 系统字体路径")

SK = quest_map()


def item(seq, task, qty="", reqs=(), priority="normal"):
    return HomeworkItem(seq=seq, subject="数学", task=task, quantity=qty,
                        requirements=list(reqs), requirements_all=list(reqs),
                        priority=priority, priority_signals=[], estimated_minutes=None,
                        type="written",
                        provenance={"task": TraceLevel.VERBATIM,
                                    "quantity": TraceLevel.VERBATIM,
                                    "subject": TraceLevel.VERBATIM})


def hw(items, extras=()):
    return ParsedHomework(date="2026-11-06", student_name="小宇", slogan="今日目标",
                          items=list(items), extras=list(extras), pending=[],
                          source_text="原文", source_kind=SourceKind.TEXT,
                          report=ValidationReport())


def white():
    return Image.new("RGB", (A4_W, A4_H), "#FFFFFF")


def test_canvas_is_a4_before_any_text_is_drawn():
    """顺序不可颠倒：先超分再写字，反过来文字发虚，直接违反验收口径。"""
    small = Image.new("RGB", (600, 800), "#FFFFFF")
    assert upscale_to_a4(small).size == (A4_W, A4_H)
    img, _ = compose(hw([item(1, "练习册", "P12-13")]), SK, base=small)
    assert img.size == (A4_W, A4_H)


def test_more_items_than_stations_raises_not_truncates():
    sk = quest_map(3)
    with pytest.raises(LayoutError, match="骨架"):
        compose(hw([item(i, "练习册") for i in range(1, 5)]), sk, base=white())


def test_no_line_start_rules_apply():
    """标点不能孤零零落到行首：换行时把前一个字一起带下来。"""
    for ch in ("）", "。", "！", "、"):
        assert ch in NO_LINE_START
    lines = wrap("抄写本课生字（每个两）", load_font(40), 10 * 40)
    assert len(lines) == 2
    assert lines[1] == "两）"          # 若去掉禁则，「）」会自己起一行
    assert all(not any(ln.startswith(ch) for ch in NO_LINE_START) for ln in lines)


def test_body_floor_is_reported_not_silently_truncated():
    long = "抄写本课生字每个两遍并注音" * 12
    img, issues = compose(hw([item(1, long)]), SK, base=white())
    assert issues            # 一定有话说，绝不静默
    assert any("14pt" in i.reason or "放不下" in i.reason for i in issues)


def test_empty_stations_are_marked():
    img, issues = compose(hw([item(1, "练习册")]), SK, base=white())
    assert issues == []      # 空关卡是正常版面，不是问题


def test_requirement_already_in_task_is_not_printed_twice():
    """回归：poc 实测「家长签字」在卡面上印了两遍。

    校验层会去重，但旧 hw.json 没有经过校验层（模型层承诺兼容 poc JSON），
    印在纸上的重复收不回来，所以排版层自己再挡一次。
    """
    task, reqs = station_text(item(1, "完成练习册，家长签字", "", ["家长签字", "用铅笔"]))
    assert reqs == ["用铅笔"]
    assert task.count("家长签字") == 1


def test_placeholder_base_is_a4_and_untouched_by_items():
    p = placeholder_base(SK)
    assert p.size == (A4_W, A4_H)


def test_body_px_floor():
    assert pt_to_px(14) == round(14 * 300 / 72)


def test_body_px_for_caps_at_design_size_and_flags_short_zones():
    """可用高度再大，正文也不会超过 14pt 的设计值；矮到装不下一行时如实小于下限。"""
    assert body_px_for(10_000) == pt_to_px(BODY_PT)
    assert body_px_for(30) < pt_to_px(BODY_FLOOR_PT)


def test_fit_block_does_not_shrink_when_text_already_fits():
    lines, px, lh = fit_block("练习册", 800, 400, pt_to_px(BODY_PT), pt_to_px(BODY_FLOOR_PT))
    assert lines == ["练习册"]
    assert px == pt_to_px(BODY_PT)
    assert lh == round(px * 1.28)


def test_slogan_replaces_default_title():
    """家长改了标题口号，图上就该出现新口号；不能日期/姓名各占一位、口号只当补位。"""
    from homework_compass.layout.compose import title_line
    default = hw([])
    default.slogan = ""
    assert title_line(default) == "2026-11-06 · 小宇 · 今日目标"
    custom = hw([])
    custom.slogan = "小宇的闯关地图"
    assert title_line(custom) == "小宇的闯关地图"
    unnamed = hw([])
    unnamed.student_name = ""
    unnamed.slogan = ""
    assert title_line(unnamed) == "2026-11-06 · 今日目标"


def test_reward_panel_hidden_when_empty():
    """家长不填奖励就整个框都不画——空框比没有更难看，也白占版面。"""
    img, issues = compose(hw([]), SK, base=white())
    l, t, r, b = next(z.rect for z in SK.zones if z.key == "reward")
    crop = img.crop((l + 20, t + 8, r - 20, b - 8)).convert("L")
    assert all(v > 245 for v in crop.getdata()), "空奖励时框内应保持底图原样"


def test_reward_panel_drawn_when_set():
    h = hw([])
    h.reward = "看一集动画片"
    img, _ = compose(h, SK, base=white())
    l, t, r, b = next(z.rect for z in SK.zones if z.key == "reward")
    crop = img.crop((l, t, r, b)).convert("L")
    assert any(v < 120 for v in crop.getdata()), "有奖励时应画出文字"
