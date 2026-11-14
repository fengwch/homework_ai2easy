"""全链路集成：两份真实原文 → 提取 → 校验 → 落盘 → 出图，默认零网络。"""

import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from homework_compass.cli.confirm import run_confirm
from homework_compass.cli.main import (
    EXIT_OK, EXIT_PARSE_PENDING, EXIT_PENDING, main,
)
from homework_compass.errors import NeedsConfirmation
from homework_compass.models import SourceKind
from homework_compass.parsing.extract import NaiveExtractor, StubExtractor
from homework_compass.pipeline import load_hw, parse_homework, render, save_hw

FIX = Path(__file__).resolve().parents[1] / "fixtures"
needs_macos_fonts = pytest.mark.skipif(sys.platform != "darwin",
                                       reason="出图需要本机 CJK 字体")

# 每份 payload 只声称对应原文里有的字：stub 一旦越界，校验层会按「零杜撰」
# 把它降级成 pending——那是另一条测试要测的东西，不是这里。
FOUR = {"items": [
    {"subject": "数学", "task": "完成练习册 P12-13", "quantity": "",
     "requirements": ["用铅笔", "家长检查后签字"]},
    {"subject": "语文", "task": "抄写本课生字", "quantity": "每个2遍",
     "requirements": ["书写工整"]},
    {"subject": "英语", "task": "听读打卡 Unit 3", "quantity": "10分钟",
     "requirements": ["APP打卡"]},
    {"subject": "美术", "task": "明天带美术材料：彩泥", "quantity": ""}],
    "extras": ["温馨提示：请今晚完成"], "unresolved": []}

FIVE = {"items": [
    {"subject": "语文", "task": "《静夜思》背诵并默写", "quantity": "",
     "requirements": ["家长签字"]},
    {"subject": "数学", "task": "练习册", "quantity": "第12-13页",
     "requirements": ["完成后校对答案"]},
    {"subject": "英语", "task": "跟读Unit3 A部分单词", "quantity": "",
     "requirements": ["APP打卡"]},
    {"subject": "科学", "task": "观察植物的变化，写一篇观察日记", "quantity": "",
     "requirements": ["下周三交"]},
    {"subject": "美术", "task": "准备好彩泥和剪刀", "quantity": ""}],
    "extras": ["明天记得穿校服", "书包里放好水彩笔"], "unresolved": []}

PAIRS = (("raw1.txt", FOUR), ("raw2.txt", FIVE))

RAW_ONE = "1.数学：完成练习册P12-13，家长签字"
ONE = {"items": [{"subject": "数学", "task": "完成练习册", "quantity": "P12-13"}],
       "extras": [], "unresolved": []}


def raw(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


@needs_macos_fonts
def test_parse_to_png_for_both_real_samples(tmp_path):
    for name, payload in PAIRS:
        hw = parse_homework(raw(name), extractor=StubExtractor(payload),
                            name="小宇", date="2026-11-06")
        assert hw.pending == [], (name, [p.text for p in hw.pending])
        r = render(hw, out_dir=tmp_path / name)
        assert (r.width, r.height, r.dpi) == (2480, 3508, (300, 300))
        with Image.open(r.path) as im:
            assert im.size == (2480, 3508)


def test_four_elements_present_on_every_item():
    """DoD §11.3 的机器部分：科目/内容必有；数量与要求至少有一类落在卡面；
       高优项必须带得出信号（星标与「重要」由排版层据此标注）。"""
    hw = parse_homework(raw("raw2.txt"), extractor=StubExtractor(FIVE))
    assert len(hw.items) == 5
    for it in hw.items:
        assert it.subject and it.task
        assert it.seq > 0
        assert it.priority in ("high", "normal")
    assert any(i.quantity for i in hw.items)
    assert sum(1 for i in hw.items if i.requirements_all) >= 3
    high = [i for i in hw.items if i.priority == "high"]
    assert high and all(i.priority_signals for i in high)
    assert hw.extras                                    # 底部「别忘了」条有内容


def test_fabricated_field_never_reaches_the_card(tmp_path):
    """DoD §11.5：注入原文没有的「用铅笔」。"""
    invented = {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13",
                           "requirements": ["用铅笔"]}], "extras": [], "unresolved": []}
    hw = parse_homework("1.数学：练习册P12-13", extractor=StubExtractor(invented))
    assert hw.items[0].requirements == []
    assert [p.text for p in hw.pending] == ["用铅笔"]
    with pytest.raises(NeedsConfirmation) as ei:
        render(hw, out_dir=tmp_path)
    assert "用铅笔" in str(ei.value)
    assert list(tmp_path.rglob("*.png")) == []


def test_omitted_item_becomes_pending():
    """DoD §11.6：原文 5 项只抽 4 项。"""
    payload = json.loads(json.dumps(FIVE))
    payload["items"] = payload["items"][:1] + payload["items"][2:]     # 漏掉数学
    hw = parse_homework(raw("raw2.txt"), extractor=StubExtractor(payload))
    texts = [p.text for p in hw.pending]
    assert any("第12-13页" in t for t in texts)
    assert any("校对答案" in t for t in texts)


def test_pending_blocks_render(tmp_path):
    hw = parse_homework(RAW_ONE, extractor=StubExtractor(ONE))
    assert [p.text for p in hw.pending] == ["家长签字"]
    with pytest.raises(NeedsConfirmation):
        render(hw, out_dir=tmp_path)
    assert list(tmp_path.rglob("*.png")) == []


@needs_macos_fonts
def test_confirm_loop_then_render_opens_the_gate(tmp_path):
    """parse → confirm → render 全链，顺带把退出码 3/2/0 各走一遍。"""
    hw = parse_homework(RAW_ONE, extractor=StubExtractor(ONE), date="2026-11-06")
    p = save_hw(hw, tmp_path / "hw.json")
    out = tmp_path / "out"

    assert main(["render", str(p), "--out", str(out)]) == EXIT_PENDING
    before = p.read_text(encoding="utf-8")
    assert run_confirm(p, stdin=io.StringIO("")) == EXIT_PARSE_PENDING   # 非 tty 不写盘
    assert p.read_text(encoding="utf-8") == before

    tty = io.StringIO("e\nrequirements\n家长签字\n")
    tty.isatty = lambda: True                # type: ignore[assignment]
    assert run_confirm(p, stdin=tty) == EXIT_OK
    assert load_hw(p).pending == []

    assert main(["render", str(p), "--out", str(out)]) == EXIT_OK
    assert len(list(out.glob("*.png"))) == 1


def test_offline_path_on_real_samples_produces_no_pending():
    expected = {"raw1.txt": 5, "raw2.txt": 6}
    for name, count in expected.items():
        hw = parse_homework(raw(name), extractor=NaiveExtractor(), date="2026-11-06")
        assert len(hw.items) == count, name
        assert hw.pending == [], (name, [p.text for p in hw.pending])


def test_json_is_the_only_hub_between_commands(tmp_path):
    hw = parse_homework(raw("raw2.txt"), extractor=StubExtractor(FIVE),
                        date="2026-11-06")
    p = save_hw(hw, tmp_path / "hw.json")
    back = load_hw(p)
    assert [i.task for i in back.items] == [i.task for i in hw.items]
    assert back.source_text == hw.source_text        # 重跑校验要靠它
    assert back.source_kind is SourceKind.TEXT
