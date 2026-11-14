import pytest

from homework_compass.errors import ExtractionError
from homework_compass.models import SourceKind, TraceLevel
from homework_compass.parsing.validate import priority_of, validate

RAW = "📚今日作业：1.数学练习册P12-13，家长检查后签字；2.语文抄写本课生字2遍；3.英语听读打卡Unit3"


def parsed(items, extras=None, unresolved=None):
    return {"items": items, "extras": extras or [], "unresolved": unresolved or []}


def test_happy_path_no_pending():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13",
                                "requirements": ["家长检查后签字"]},
                               {"subject": "语文", "task": "抄写本课生字", "quantity": "2遍"},
                               {"subject": "英语", "task": "听读打卡", "quantity": "Unit3"}]))
    assert len(hw.items) == 3 and hw.pending == []


def test_fabricated_requirement_dropped_rest_kept():
    """原文没有「用铅笔」，只丢这条要求，其余照常上图。"""
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13",
                                "requirements": ["用铅笔", "家长检查后签字"]}]))
    assert hw.items[0].requirements == ["家长检查后签字"]
    assert any(p.text == "用铅笔" for p in hw.pending)


def test_fabricated_subject_blanked_not_shown():
    hw = validate(RAW, parsed([{"subject": "音乐", "task": "练习册", "quantity": "P12-13"}]))
    assert hw.items[0].subject == ""
    assert any("音乐" in p.text for p in hw.pending)


def test_whole_task_fabricated_drops_item():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "观察天象", "quantity": ""}]))
    assert hw.items == []


def test_empty_task_dropped_with_note():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "", "quantity": ""}]))
    assert hw.items == [] and hw.report.notes


def test_seq_renumbered_after_drops():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"},
                               {"subject": "体育", "task": "观察天象", "quantity": ""},
                               {"subject": "语文", "task": "抄写本课生字", "quantity": "2遍"}]))
    assert [i.seq for i in hw.items] == [1, 2]


def test_priority_program_overrides_llm():
    hw = validate(RAW, parsed([{"subject": "语文", "task": "抄写本课生字",
                                "quantity": "2遍", "priority": "high"}]))
    assert hw.items[0].priority == "normal"
    assert hw.report.priority_overrides


def test_priority_marker_survives_requirement_dedup():
    """整句当 task、又重复列要求时，去重不能把「签字」信号一起去掉。"""
    text = "1.数学：完成练习册，家长签字"
    hw = validate(text, parsed([{"subject": "数学", "task": "完成练习册，家长签字",
                                 "quantity": "", "requirements": ["家长签字"]}]))
    assert hw.items[0].requirements == []
    assert hw.items[0].requirements_all == ["家长签字"]
    assert hw.items[0].priority == "high"


def test_invalid_type_becomes_unknown():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册",
                                "quantity": "P12-13", "type": "考试"}]))
    assert hw.items[0].type == "unknown"


def test_fabricated_extra_becomes_pending():
    hw = validate(RAW, parsed([], extras=["带跳绳"]))
    assert hw.extras == []


@pytest.mark.parametrize("bad", ["not-a-dict", {"no_items": 1}, {"items": "x"}])
def test_structural_failure_raises_not_silently(bad):
    with pytest.raises(ExtractionError):
        validate(RAW, bad if isinstance(bad, dict) else {})


def test_provenance_recorded_per_field():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "完成练习册",
                                "quantity": "P12-13"}]))
    assert hw.items[0].provenance["quantity"] is TraceLevel.VERBATIM
    assert hw.items[0].provenance["task"] is TraceLevel.PARTIAL


def test_pending_flagged_in_advisories_not_blocked():
    """规范化过但采信的字段绝不进 pending，否则补动词就出不了图。

    破折号写法（P12-13 → P12–13）不算规范化：norm 剥掉全部标点后两者相同，
    判 VERBATIM，连 advisory 都不进。真正会进 advisory 的是 task 补动词。
    """
    text = "1.数学练习册P12-13"
    hw = validate(text, parsed([{"subject": "数学", "task": "完成练习册",
                                 "quantity": "P12–13"}]))
    assert hw.pending == []
    assert hw.items[0].task == "完成练习册"
    assert any(r.level is TraceLevel.PARTIAL for r in hw.report.advisories)


def test_fabricated_page_number_is_not_adopted():
    """页码零容错（spec §5.2）：原文只有 P12-13 时，P14-15 不得上图。

    不采信这个页码——置空并留痕，绝不把错页码印到孩子桌上。
    """
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P14-15"}]))
    assert hw.items[0].quantity == ""
    assert hw.items[0].provenance["quantity"] is TraceLevel.UNSOURCED
    assert any("quantity" in n or "页码" in n for n in hw.report.notes)


def test_priority_of_returns_signals():
    priority, signals = priority_of("数学 家长签字")
    assert priority == "high" and "签字" in signals
    assert priority_of("数学 练习册") == ("normal", [])


def test_requirements_given_as_string_not_exploded():
    """模型把单个要求写成裸字符串时，不能逐字符展开成一条条要求。"""
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13",
                                "requirements": "家长检查后签字"}]))
    assert hw.items[0].requirements == ["家长检查后签字"]


def test_extras_given_as_string_treated_as_one_item():
    text = "1.数学练习册P12-13；带跳绳"
    hw = validate(text, parsed([{"subject": "数学", "task": "练习册",
                                 "quantity": "P12-13"}], extras="带跳绳"))
    assert hw.extras == ["带跳绳"]
