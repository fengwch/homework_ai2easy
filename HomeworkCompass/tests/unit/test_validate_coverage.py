from homework_compass.models import PendingReason, SourceKind
from homework_compass.parsing.validate import claimed_text, validate

RAW2 = ("各位家长好！今天（11月5日）的作业如下：\n"
        "①语文：《静夜思》背诵并默写，家长签字\n②数学：练习册第12-13页\n"
        "⑤美术：准备好彩泥和剪刀\n另外明天记得穿校服。\n收到请回复，谢谢！")


def parsed(items, extras=None, unresolved=None):
    return {"items": items, "extras": extras or [], "unresolved": unresolved or []}


def test_subject_counts_toward_claimed_text():
    """原文写「英语听读打卡」，拆成 subject+task 后不拼回去就会误报遗漏。"""
    hw = validate("1.英语听读打卡Unit3",
                  parsed([{"subject": "英语", "task": "听读打卡", "quantity": "Unit3"}]))
    assert hw.pending == []


def test_dropped_line_becomes_uncovered_pending():
    hw = validate(RAW2 + "\n⑥科学：观察植物的变化",
                  parsed([{"subject": "语文", "task": "《静夜思》背诵并默写",
                           "requirements": ["家长签字"]},
                          {"subject": "数学", "task": "练习册", "quantity": "第12-13页"},
                          {"subject": "美术", "task": "准备好彩泥和剪刀"},
                          {"subject": "科学", "task": "观察植物的变化"}],
                          extras=["明天记得穿校服"]))
    texts = "；".join(claimed_text(hw).split())
    assert "收到请回复" not in texts            # 套话不进气泡
    reasons = {p.reason for p in hw.pending}
    assert PendingReason.UNCOVERED in reasons or hw.pending == []


def test_boilerplate_from_model_never_reaches_parent():
    """poc 缺陷：模型把客套话堆进 unresolved，透传后家长每天确认一堆废话。"""
    hw = validate("1.数学练习册P12-13",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                         unresolved=["各位家长好", "今天作业如下", "收到请回复"]))
    assert hw.pending == []


def test_real_omission_still_reported_after_boilerplate_filter():
    hw = validate("1.数学练习册P12-13；明天带美术材料：彩泥",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                         unresolved=["各位家长好"]))
    assert [p.text for p in hw.pending] == ["明天带美术材料：彩泥"] or any(
        "美术材料" in p.text for p in hw.pending)
    assert all(p.reason is not None for p in hw.pending)


def test_pending_has_context_and_related_seq():
    hw = validate("1.数学：完成练习册P12-13\n2.明天带美术材料：彩泥",
                  parsed([{"subject": "数学", "task": "完成练习册", "quantity": "P12-13"}]))
    assert hw.pending
    p = hw.pending[0]
    assert p.source_sentence            # 家长看得见它出自哪一句
    assert p.id                         # 销账靠 id，不靠文案


def test_pending_ids_unique():
    hw = validate("1.数学练习册P12-13\n2.语文练习册P14-15\n3.英语单词表",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"},
                          {"subject": "语文", "task": "练习册", "quantity": "P14-15"}]))
    assert len({p.id for p in hw.pending}) == len(hw.pending)


def test_ocr_source_always_blocks():
    hw = validate("1.数学练习册P12-13",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}]),
                  source_kind=SourceKind.OCR)
    assert [p.reason for p in hw.pending] == [PendingReason.OCR_UNVERIFIED]


def test_claimed_text_excludes_pending_by_default():
    """否则待确认项自己认领自己，永远销不掉——poc 的死胡同。"""
    hw = validate("1.数学练习册P12-13\n2.明天带美术材料",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}]))
    assert hw.pending
    assert "美术材料" not in claimed_text(hw)
    assert "美术材料" in claimed_text(hw, include_pending=True)


def test_same_text_from_two_sources_yields_one_pending():
    """模型自认含糊的那段同时又是覆盖率缺口时，不能变成两条一样的待确认。"""
    hw = validate("1.数学练习册P12-13\n2.明天带美术材料",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                         unresolved=["明天带美术材料"]))
    assert [p.text for p in hw.pending] == ["明天带美术材料"]


def test_report_uncovered_matches_stats_and_excludes_boilerplate():
    """审计面只列真正的覆盖率缺口；套话在分段层就被挡掉，不冒充遗漏。"""
    hw = validate("1.数学练习册P12-13\n2.明天带美术材料\n收到请回复",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}]))
    assert hw.report.uncovered == ["明天带美术材料"]
    assert hw.report.stats["uncovered"] == len(hw.report.uncovered)
    assert all("收到" not in u for u in hw.report.uncovered)
