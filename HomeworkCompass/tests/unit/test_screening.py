import sys
import pytest
from homework_compass.parsing.extract import naive_extract
from homework_compass.parsing.validate import validate


RAW = """（11月6日）
1、大声拼读p51-52三遍
2、朗读p53儿歌《家》三遍，并尝试续编句子
3、预习p54-55
4、查P47-53
5、说一说【请看班优】
6、英语读u1-u2
7、23
8、&
9、敬
"""


def test_junk_fragments_do_not_become_items():
    """纯数字、纯符号、单字、纯日期都不是一条作业，不该进清单。"""
    hw = validate(RAW, naive_extract(RAW), date="2026-11-06", name="小宇")
    tasks = [i.task for i in hw.items]
    for junk in ("23", "&", "敬"):
        assert junk not in tasks, tasks
    # 真正的六条必须还在
    assert len(hw.items) == 6, tasks
    # 纯数字残片有实际信息（可能是某条作业的量），要回问家长
    assert any("23" in p.text for p in hw.pending)
    # 「敬」是「敬请家长签字」的残片，本身没有任务语义，不该打扰家长
    assert not any(p.text.strip() == "敬" for p in hw.pending)


def test_short_but_meaningful_fragments_survive():
    """「背」「写」这种单字动词是真实作业的简写，不能当成垃圾丢掉。"""
    raw = "1.背\n2.写\n3.预习p54-55"
    hw = validate(raw, naive_extract(raw))
    tasks = [i.task for i in hw.items]
    assert "背" in tasks
    assert "写" in tasks
    assert "预习p54-55" in tasks


def test_meaningful_single_char_is_not_swallowed_by_coverage_check():
    """单字「背」即使没被抽取层接住，也必须作为缺口回到家长面前。"""
    from homework_compass.parsing.segmentation import split_chunks
    assert "背" in split_chunks("1.背\n2.预习p54-55")


def test_model_unresolved_junk_is_dropped():
    """LLM 把残字放进 unresolved 时，也不该变成待确认项。"""
    from homework_compass.parsing.validate import validate
    raw = "1.大声拼读p51-52三遍\n敬"
    hw = validate(raw, {"items": [{"task": "大声拼读p51-52三遍"}],
                        "extras": [], "unresolved": ["敬", "23"]})
    texts = [p.text for p in hw.pending]
    # 残字和孤立数字都不是一条作业，模型报了也不该打扰家长
    assert "敬" not in texts
    assert "23" not in texts


def test_low_information_number_still_surfaces():
    """孤立数字不构成作业条目，但仍会作为原文缺口回问家长（零遗漏）。
    家长点一次「忽略」即可，这是刻意的取舍。"""
    from homework_compass.parsing.validate import validate
    raw = "1、大声拼读p51-52三遍\n7、23"
    hw = validate(raw, {"items": [{"task": "大声拼读p51-52三遍"}],
                        "extras": [], "unresolved": []})
    assert any("23" in p.text for p in hw.pending)
    assert all("23" != i.task for i in hw.items)
    from homework_compass.parsing.validate import dismiss
    after = dismiss(hw, hw.pending[0].id)
    assert after.pending == []
