import pytest

from homework_compass.models import PendingReason, SourceKind, TraceLevel
from homework_compass.parsing.validate import correct, dismiss, is_covered, validate

RAW = "1.数学：完成练习册P12-13\n2.明天带美术材料：彩泥"


def hw_with_pending():
    return validate(RAW, {"items": [{"subject": "数学", "task": "完成练习册",
                                     "quantity": "P12-13"}],
                          "extras": [], "unresolved": []})


def test_confirmation_loop_is_not_a_dead_end():
    """poc 初版：--set 改完字段，unresolved 永远清不掉，图永远生不成。"""
    hw = hw_with_pending()
    assert hw.pending
    after = correct(hw, seq=1, field="requirements", value="明天带美术材料：彩泥")
    assert after.pending == []


def test_correct_on_wrong_target_keeps_pending():
    hw = hw_with_pending()
    after = correct(hw, seq=1, field="quantity", value="P12-14")
    assert after.pending == hw.pending      # 没承接上就留着，宁可多问一次


def test_original_object_not_mutated():
    hw = hw_with_pending()
    before = [p.id for p in hw.pending]
    correct(hw, seq=1, field="requirements", value="明天带美术材料：彩泥")
    assert [p.id for p in hw.pending] == before


def test_dismiss_only_touches_named_pending():
    hw = validate("1.数学练习册P12-13\n2.明天带美术材料\n3.后天交科学记录单",
                  {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                   "extras": [], "unresolved": []})
    assert len(hw.pending) >= 2
    target = hw.pending[0]
    after = dismiss(hw, target.id)
    assert target.id not in [p.id for p in after.pending]
    assert [p.text for p in after.pending] == [p.text for p in hw.pending[1:]]


def test_ocr_pending_can_be_dismissed():
    hw = validate("1.数学练习册P12-13",
                  {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                   "extras": [], "unresolved": []}, source_kind=SourceKind.OCR)
    pid = next(p.id for p in hw.pending if p.reason is PendingReason.OCR_UNVERIFIED)
    assert dismiss(hw, pid).pending == []


@pytest.mark.parametrize("field", ["seq", "provenance", "requirements_all", "nope"])
def test_non_whitelist_field_rejected(field):
    from homework_compass.parsing.validate import EDITABLE_FIELDS
    hw = hw_with_pending()
    with pytest.raises(ValueError, match="白名单"):
        correct(hw, seq=1, field=field, value="x")
    assert "task" in EDITABLE_FIELDS and "d1" not in EDITABLE_FIELDS


def test_is_covered_excludes_pending_itself():
    hw = hw_with_pending()
    p = hw.pending[0]
    assert not is_covered(p.text, hw)


def test_manual_correction_is_recorded_in_notes():
    hw = hw_with_pending()
    after = correct(hw, seq=1, field="requirements", value="明天带美术材料：彩泥")
    assert any("家长修正" in n for n in after.report.notes)


def test_corrected_field_is_not_claimed_verbatim():
    """家长改出来的值不在原文里，审计数据不能还写着 verbatim。"""
    hw = hw_with_pending()
    after = correct(hw, seq=1, field="quantity", value="P12-14")
    assert after.items[0].quantity == "P12-14"
    assert after.items[0].provenance["quantity"] is TraceLevel.NORMALIZED


def test_correct_recomputes_priority():
    hw = hw_with_pending()
    after = correct(hw, seq=1, field="requirements", value="家长签字")
    assert after.items[0].priority == "high"
    assert "签字" in after.items[0].priority_signals


def test_correct_rejects_type_outside_enum():
    """可改不等于乱改：type 仍只能取枚举内的值。"""
    hw = hw_with_pending()
    with pytest.raises(ValueError, match="type"):
        correct(hw, seq=1, field="type", value="考试")
    assert correct(hw, seq=1, field="type", value="reading").items[0].type == "reading"


def test_correct_refreshes_uncovered_report():
    """改对了就不该再在审计面上显示「原文有、数据没有」。"""
    hw = hw_with_pending()
    # 冒号也分词块，所以一句「明天带美术材料：彩泥」是两条待确认（
    # poc 同口径：一个已认领的词不能掩盖剩下的遗漏）。
    assert hw.report.uncovered == ["明天带美术材料", "彩泥"]
    after = correct(hw, seq=1, field="requirements", value="明天带美术材料：彩泥")
    assert after.report.uncovered == []
    assert after.report.stats["uncovered"] == 0


def test_drop_item_removes_item_and_renumbers():
    """照片 OCR 后的清单常有一两行是噪声；家长要能整条删掉，而不是逐字段清空。"""
    from homework_compass.parsing.validate import drop_item
    raw = "1.数学：完成练习册P12-13\n2.语文：抄写生字\n3.英语：跟读Unit3"
    hw = validate(raw, {"items": [
        {"subject": "数学", "task": "完成练习册P12-13"},
        {"subject": "语文", "task": "抄写生字"},
        {"subject": "英语", "task": "跟读Unit3"},
    ], "extras": [], "unresolved": []})
    after = drop_item(hw, 2)
    assert [(i.seq, i.task) for i in after.items] == [
        (1, "完成练习册P12-13"), (2, "跟读Unit3")]
    # 被删那条的原文不会被悄悄吞掉：没被别的项承接，就回到待确认
    assert any("抄写生字" in p.text for p in after.pending)


def test_drop_item_keeps_content_unclaimed_elsewhere():
    """删项不是让内容「消失」：原文里没被别的项承接的整句仍要回问，宁缺毋编。"""
    from homework_compass.parsing.validate import drop_item
    raw = "1.数学：完成练习册P12-13\n2.明天带美术材料：彩泥"
    hw = validate(raw, {"items": [
        {"subject": "数学", "task": "完成练习册P12-13"},
        {"task": "明天带美术材料：彩泥"},
    ], "extras": [], "unresolved": []})
    assert hw.pending == []
    after = drop_item(hw, 2)
    assert [i.task for i in after.items] == ["完成练习册P12-13"]
    assert any("美术材料" in p.text for p in after.pending)


def test_drop_item_unknown_seq_raises():
    import pytest
    from homework_compass.parsing.validate import drop_item
    hw = validate("1.数学：完成练习册P12-13",
                  {"items": [{"subject": "数学", "task": "完成练习册P12-13"}],
                   "extras": [], "unresolved": []})
    with pytest.raises(ValueError, match="找不到第 9 项"):
        drop_item(hw, 9)
