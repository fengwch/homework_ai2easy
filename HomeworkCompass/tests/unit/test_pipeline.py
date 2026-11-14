import sys
from pathlib import Path

import pytest
from PIL import Image

from homework_compass.errors import FontError, NeedsConfirmation
from homework_compass.models import SourceKind
from homework_compass.parsing.extract import StubExtractor
from homework_compass.pipeline import (
    correct, dismiss, load_hw, parse_homework, render, save_hw, text_from_image,
)

pytestmark = pytest.mark.skipif(sys.platform != "darwin",
                                reason="候选表是 macOS 系统字体路径")

RAW = "1.数学：完成练习册P12-13，家长签字\n2.明天带美术材料：彩泥"
GOOD = {"items": [{"subject": "数学", "task": "完成练习册", "quantity": "P12-13",
                   "requirements": ["家长签字"]},
                  {"subject": "", "task": "明天带美术材料", "quantity": "",
                   "requirements": ["彩泥"]}],
        "extras": [], "unresolved": []}
# 单项用的 raw/stub：stub 说的每个字都得出自 raw，否则校验层会（正确地）判杜撰
ONE_RAW = "1.数学：练习册P12-13"
ONE = {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
       "extras": [], "unresolved": []}
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
LONG = "抄写本课生字每个两遍并注音" * 12


def test_parse_uses_injected_extractor():
    hw = parse_homework(RAW, extractor=StubExtractor(GOOD), name="小宇",
                        date="2026-11-06")
    assert len(hw.items) == 2 and hw.pending == []
    assert hw.student_name == "小宇" and hw.date == "2026-11-06"


def test_default_extractor_is_offline_not_paid():
    """库的默认路径不许花钱、不许联网。在线是调用方显式注入的事。"""
    hw = parse_homework("1.数学：练习册P12-13")
    assert len(hw.items) == 1


def test_render_refuses_when_pending_blocked(tmp_path):
    hw = parse_homework(RAW, extractor=StubExtractor({"items": [
        {"subject": "数学", "task": "完成练习册", "quantity": "P12-13"}],
        "extras": [], "unresolved": []}))
    assert hw.pending
    with pytest.raises(NeedsConfirmation):
        render(hw, out_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []          # 拒绝就不许留半成品


def test_render_writes_a4_300dpi_png(tmp_path):
    hw = parse_homework(RAW, extractor=StubExtractor(GOOD))
    r = render(hw, out_dir=tmp_path, base_dir=tmp_path / "no_bases")
    assert (r.width, r.height) == (2480, 3508) and r.dpi == (300, 300)
    with Image.open(r.path) as im:
        assert im.size == (2480, 3508)
    assert r.used_placeholder is True               # 没传 --base 就是预览件
    assert r.issues == []


def test_render_with_real_base_is_not_placeholder(tmp_path):
    bp = tmp_path / "base.png"
    Image.new("RGB", (1240, 1754), "#EEF").save(bp)
    hw = parse_homework(RAW, extractor=StubExtractor(GOOD))
    r = render(hw, base=bp, out_dir=tmp_path)
    assert r.used_placeholder is False


def test_render_problems_are_carried_not_swallowed(tmp_path):
    """版面问题进 RenderResult.issues，不是吞掉，也不是拒绝出图。

    raw 里必须真的含这段长文：unsourced 的项会被降级成 pending，
    那样 render 会先按闸门拒绝，测不到 issues。
    """
    hw = parse_homework(LONG, extractor=StubExtractor({"items": [
        {"subject": "", "task": LONG, "quantity": ""}],
        "extras": [], "unresolved": []}))
    assert hw.pending == []
    r = render(hw, out_dir=tmp_path, base_dir=tmp_path / "no_bases")
    assert r.issues


def test_roundtrip_through_json(tmp_path):
    hw = parse_homework(RAW, extractor=StubExtractor(GOOD))
    p = save_hw(hw, tmp_path / "hw.json")
    back = load_hw(p)
    assert [i.task for i in back.items] == [i.task for i in hw.items]
    assert back.source_text == hw.source_text


def test_correct_and_dismiss_go_through_the_parsing_layers_rules():
    """pipeline 只转发，不另立一套销账规则：补字段和按 id 销账都要真的生效。"""
    hw = parse_homework(RAW, extractor=StubExtractor({"items": [
        {"subject": "数学", "task": "完成练习册", "quantity": "P12-13"},
        {"subject": "", "task": "明天带美术材料", "quantity": ""}],
        "extras": [], "unresolved": []}))
    assert {p.text for p in hw.pending} == {"家长签字", "彩泥"}

    cleared = correct(hw, 1, "requirements", "家长签字，彩泥")
    assert cleared.pending == []           # 承接上了就销账
    assert hw.pending                      # 入参不被就地改写

    one = dismiss(hw, hw.pending[0].id)
    assert len(one.pending) == len(hw.pending) - 1
    assert any("家长确认不纳入" in n for n in one.report.notes)


def test_text_from_image_returns_ocr_kind(monkeypatch):
    from homework_compass import pipeline
    monkeypatch.setattr(pipeline, "ocr_to_text", lambda p, **kw: "1.数学练习册")
    text, kind = pipeline.text_from_image(Path("x.jpg"))
    assert kind is SourceKind.OCR and text == "1.数学练习册"


def test_configured_font_candidates_are_used(tmp_path):
    """spec §6.4「候选表可被配置覆盖」：配置里给的字体要真的被拿去解析。"""
    hw = parse_homework(ONE_RAW, extractor=StubExtractor(ONE))
    with pytest.raises(FontError, match="字形覆盖"):
        render(hw, out_dir=tmp_path, fonts=[ARIAL])
    r = render(hw, out_dir=tmp_path, fonts=[ARIAL, CJK])
    assert r.path.is_file()


def test_output_name_cannot_escape_out_dir(tmp_path):
    """date 可能来自模型或 --date，含 `../` 时不能把文件写到 out_dir 之外。"""
    hw = parse_homework(ONE_RAW, extractor=StubExtractor(ONE),
                        date="../../etc/2026-11-06")
    r = render(hw, out_dir=tmp_path, base_dir=tmp_path / "no_bases")
    assert r.path.parent == tmp_path
    assert ".." not in r.path.name and "/" not in r.path.name


def _sources(sub: str | None = None) -> dict[str, str]:
    root = Path(__file__).resolve().parents[2] / "src" / "homework_compass"
    files = (root / sub).rglob("*.py") if sub else root.rglob("*.py")
    return {str(f.relative_to(root)): f.read_text(encoding="utf-8") for f in files}


def test_layout_never_imports_parsing():
    """spec §2 的依赖方向不是文档愿望：排版与校验必须各自能被单独测试复用。

    只查 `homework_compass.parsing` 这个导入路径，不查裸词 "parsing"：
    后者会被一句提到 `parse_homework` 的注释误伤，假阳性的拦截测试没人愿意维护。"""
    for name, text in _sources("layout").items():
        assert "homework_compass.parsing" not in text, name


def test_parsing_never_imports_layout():
    for name, text in _sources("parsing").items():
        assert "homework_compass.layout" not in text, name


def test_only_confirm_module_reads_the_terminal():
    """「库不做任何 IO 交互」必须能被机器检查，否则下一个 PR 就能塞进去一个 input()。"""
    for name, text in _sources().items():
        if name.startswith("cli/confirm.py"):
            continue
        assert "sys.stdin" not in text, name
        assert "input(" not in text, name
