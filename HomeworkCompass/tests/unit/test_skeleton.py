import inspect

import pytest

from homework_compass.layout.skeleton import (
    A4_DPI, A4_H, A4_W, MIN_MARGIN_PX, SKELETONS, Zone, ZoneKind,
    build_prompt, get_skeleton, quest_map, skin_palette, zones_report,
)


def px(v: float, axis: str) -> float:
    return v * (A4_W if axis == "x" else A4_H)


def test_a4_constants_are_exactly_as_spec():
    assert (A4_W, A4_H, A4_DPI) == (2480, 3508, 300)


def test_quest_map_has_six_stations_and_one_extras():
    """poc 实测：6 个关卡位 + 1 条易漏项带，超过 6 项必须换骨架或分页。"""
    sk = quest_map()
    assert len(sk.stations) == 6
    assert [z.px for z in sk.stations] == [1, 2, 3, 4, 5, 6]
    assert sum(1 for z in sk.zones if z.kind is ZoneKind.EXTRAS) == 1


def test_every_zone_respects_ten_mm_margin():
    """spec §6.3：边距不达标要在骨架构造期就失败，不靠人记。"""
    sk = quest_map()
    for z in sk.zones:
        assert px(z.x, "x") >= MIN_MARGIN_PX, z.key
        assert px(1 - z.x - z.w, "x") >= MIN_MARGIN_PX, z.key
        assert px(z.y, "y") >= MIN_MARGIN_PX, z.key
        assert px(1 - z.y - z.h, "y") >= MIN_MARGIN_PX, z.key


def test_out_of_margin_zone_raises_at_construction():
    with pytest.raises(ValueError, match="页边距"):
        Zone("bad", ZoneKind.STATION, 0.01, 0.5, 0.4, 0.1, px=1)


def test_zones_do_not_overlap_each_other():
    sk = quest_map()
    rects = [z.rect for z in sk.zones]
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (a, b)


def test_rect_is_normalized_to_pixels():
    z = Zone("t", ZoneKind.TITLE, 0.08, 0.035, 0.84, 0.072, role="标题")
    l, t, r, b = z.rect
    assert (l, t) == (round(0.08 * A4_W), round(0.035 * A4_H))
    assert r > l and b > t


def test_station_count_bounds():
    # 6 是几何上限：第 7 关会撞上易漏项带并破 10mm 边距（poc 曾允许到 8，但会画到纸外）。
    for n in (0, 2, 7, 8, 9):
        with pytest.raises(ValueError):
            quest_map(n)


def test_registry_is_pure_data_extension_point():
    assert set(SKELETONS) == {"quest-map"}
    assert SKELETONS["quest-map"]().name == "quest-map"


# ---- build_prompt：单一事实来源不变量的另一半，本版不调用但必须留在库里 ----

def test_prompt_describes_every_zone_spatially():
    sk = quest_map()
    p = build_prompt(sk, "dinosaur")
    for z in sk.zones:
        assert f"{round(z.x * 100, 1)}%" in p
        assert f"{round((z.y + z.h) * 100, 1)}%" in p


def test_prompt_forbids_any_text_in_boxes():
    p = build_prompt(quest_map(), "space")
    assert "框内不得绘制任何文字" in p
    assert "汉字" in p and "水印" in p


def test_prompt_never_receives_homework_text():
    """签名里只有骨架与皮肤——做不到「不传文字」就是契约失效。"""
    params = list(inspect.signature(build_prompt).parameters)
    assert params == ["skeleton", "skin"]


def test_prompt_mentions_station_count():
    assert "6 个关卡框" in build_prompt(quest_map(), "dinosaur")


def test_skin_palette_always_has_accent():
    assert skin_palette("nonexistent")["accent"].startswith("#")


def test_unknown_skeleton_name_is_a_loud_error():
    """退出码契约要求「未知骨架」是 4，不是一个漂进终端的 KeyError。"""
    with pytest.raises(ValueError, match="quest-map"):
        get_skeleton("nope")


def test_known_name_returns_the_skeleton():
    assert get_skeleton("quest-map").name == "quest-map"
