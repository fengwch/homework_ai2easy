"""poc 期间四个真实 bug，每个一条具名测试。它们的共同点：都不报错。"""

import re

from homework_compass.models import PendingReason, SourceKind
from homework_compass.parsing.extract import StubExtractor
from homework_compass.parsing.validate import claimed_text, is_covered, validate
from homework_compass.pipeline import correct, dismiss, parse_homework, render

RAW_ONE = "1.数学：完成练习册P12-13，家长签字"
ONE = {"items": [{"subject": "数学", "task": "完成练习册", "quantity": "P12-13"}],
       "extras": [], "unresolved": []}


def test_confirmation_loop_is_not_a_dead_end(tmp_path):
    """曾经：poc 初版 `--set` 改完字段，unresolved 永远清不掉，
       确认环节能进不能出，图永远生不成（实测 EXIT=3 卡死）。"""
    hw = parse_homework(RAW_ONE, extractor=StubExtractor(ONE))
    assert [p.text for p in hw.pending] == ["家长签字"]
    after = correct(hw, 1, "requirements", "家长签字")
    assert after.pending == []
    render(after, out_dir=tmp_path)                  # 现在画得出来了


def test_boilerplate_never_reaches_parent():
    """曾经：模型把「各位家长好！今天作业如下：」原样塞进 unresolved，
       poc 透传给家长，一次跑出 8 条假待确认项——产品直接没法用。"""
    raw = ("各位家长好！今天（11月5日）的作业如下：\n1.数学练习册P12-13\n收到请回复，谢谢！")
    hw = validate(raw, {"items": [{"subject": "数学", "task": "练习册",
                                   "quantity": "P12-13"}],
                        "extras": [],
                        "unresolved": ["各位家长好", "今天作业如下", "收到请回复", "谢谢"]})
    assert hw.pending == []
    assert hw.report.stats["auto_dropped_boilerplate"] >= 3


def _norm(text: str) -> str:
    """去掉标点与空白：原文在「：」处会被拆成两条 pending，拼起来才是原句。"""
    return re.sub(r"[\W_]", "", text)


def test_real_homework_never_auto_dropped():
    """套话过滤的危险方向：把真作业当客话吞掉。这条测试存在的意义就是
       防止上条测试被「优化」成一律丢弃。"""
    real = ["明天带美术材料：彩泥", "今晚十点前完成", "后天交观察日记",
            "周一带上跳绳", "收到书本后签字"]
    for line in real:
        hw = validate(f"1.数学练习册P12-13；{line}", {"items": [
            {"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
            "extras": [], "unresolved": []})
        surfaced = _norm("".join(p.text for p in hw.pending))
        assert _norm(line) in surfaced, line


def test_requirement_not_printed_twice():
    """曾经：渲染出的 A4 上「家长签字/APP打卡/校对答案/下周三交」各印两遍——
       模型把整句当 task、又把句尾要求单列一份，两边都上图。"""
    text = "1.数学：完成练习册P12-13，家长签字"
    hw = validate(text, {"items": [{"subject": "数学", "task": "完成练习册P12-13，家长签字",
                                    "quantity": "", "requirements": ["家长签字"]}],
                         "extras": [], "unresolved": []})
    it = hw.items[0]
    assert it.requirements == []                       # 显示层不重复
    assert it.requirements_all == ["家长签字"]         # 判定层仍生效
    assert it.priority == "high"


def test_pending_does_not_cover_itself():
    """曾经：claimed_text() 把 unresolved 也算进「已认领」，
       于是每条待确认项自己认领自己，一条都销不掉。"""
    hw = validate(RAW_ONE, ONE)
    p = hw.pending[0]
    assert p.text in claimed_text(hw, include_pending=True)
    assert not is_covered(p.text, hw)


def test_ocr_notice_can_be_cleared():
    """曾经：OCR 强制确认项在销账**之后**才追加，于是它永远清不掉（同类死胡同）。"""
    hw = validate("1.数学练习册P12-13", {"items": [{"subject": "数学", "task": "练习册",
                                                    "quantity": "P12-13"}],
                                         "extras": [], "unresolved": []},
                  source_kind=SourceKind.OCR)
    pid = next(p.id for p in hw.pending if p.reason is PendingReason.OCR_UNVERIFIED)
    assert dismiss(hw, pid).pending == []


def test_connector_prefixed_line_not_double_reported():
    """曾经：原文「另外明天记得穿校服」，extras 已有「明天记得穿校服」，
       不剥连接词就误报一条遗漏。"""
    hw = validate("1.数学练习册P12-13\n另外明天记得穿校服",
                  {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                   "extras": ["明天记得穿校服"], "unresolved": []})
    assert hw.pending == []
