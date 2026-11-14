import pytest

from homework_compass.models import (
    ADVISORY_LEVELS, HomeworkItem, ParsedHomework, PendingItem, PendingReason,
    SourceKind, TraceLevel, TRACE_ACCEPTED, ValidationReport, from_json,
    make_pending_id, to_json,
)


def test_unsourced_is_not_accepted_but_partial_is():
    assert TraceLevel.UNSOURCED not in TRACE_ACCEPTED
    assert TraceLevel.PARTIAL in TRACE_ACCEPTED


def test_advisory_levels_never_block():
    """规范化判定只提示不阻断，否则 P12-13→P12–P13 会卡死整个流程。"""
    assert ADVISORY_LEVELS == {TraceLevel.NORMALIZED, TraceLevel.TOKENS_MATCH, TraceLevel.PARTIAL}


def test_pending_id_is_stable_and_text_sensitive():
    a = make_pending_id(PendingReason.UNCOVERED, "明天带美术材料")
    b = make_pending_id(PendingReason.UNCOVERED, "明天带美术材料")
    c = make_pending_id(PendingReason.UNCOVERED, "明天带美术材料：彩泥")
    assert a == b and a != c


def test_roundtrip_preserves_pending():
    """pending 必须带真内容：空列表 roundtrip 什么都验不到。"""
    p = PendingItem(id=make_pending_id(PendingReason.UNCOVERED, "明天带美术材料"),
                    text="明天带美术材料", reason=PendingReason.UNCOVERED,
                    source_sentence="", related_seq=None)
    it = HomeworkItem(seq=1, subject="数学", task="练习册", quantity="P12-13",
                      requirements=["用铅笔"], requirements_all=["用铅笔"],
                      priority="normal", priority_signals=[], estimated_minutes=None,
                      type="written", provenance={"task": TraceLevel.VERBATIM})
    hw = ParsedHomework(date="2026-11-06", student_name="小宇", slogan="", items=[it],
                        extras=[], pending=[p], source_text="原文",
                        source_kind=SourceKind.TEXT)
    plain = to_json(hw)
    # type is str 而不是 isinstance：混入 str 的枚举 isinstance 也过关，那正是陷阱
    assert type(plain["pending"][0]["reason"]) is str
    # unresolved 是 pending 的文本投影，旧工具只认这个键（spec §4）
    assert plain["unresolved"] == ["明天带美术材料"]
    # provenance 里的枚举在 asdict 后仍是 Enum，靠 _plain 拆掉
    assert type(plain["items"][0]["provenance"]["task"]) is str
    assert plain["items"][0]["provenance"]["task"] == "verbatim"
    back = from_json(plain)
    assert back.source_text == "原文"
    assert back.pending == [p]
    assert back.pending[0].reason is PendingReason.UNCOVERED
    assert back.source_kind is SourceKind.TEXT
    assert back.items[0].provenance["task"] is TraceLevel.VERBATIM
    assert back.items[0].requirements_all == ["用铅笔"]


def test_roundtrip_survives_padded_pending_text():
    """pending 文案带空白时，往返读必须成功——否则 save→load 会把 hw.json 变成废纸。

    to_json 写的 unresolved 是 pending 文案的投影，两边归一化不一致时
    from_json 会误判成「冲突」，CLI 会报一句莫名其妙的话。
    """
    hw = from_json({"pending": [{"text": "  甲  ", "reason": "uncovered"}]})
    assert hw.pending[0].text == "甲"
    back = from_json(to_json(hw))
    assert back.pending[0].text == "甲"
    assert back.pending[0].id == hw.pending[0].id


def test_audit_dicts_and_empty_requirements_survive_roundtrip():
    """priority_overrides 是 list[dict]；显式的 requirements_all=[] 不得被 requirements 覆盖。"""
    overrides = [{"where": "item1.task", "llm": "high", "program": "normal"}]
    hw = ParsedHomework(date="2026-11-06", student_name="小宇", slogan="", items=[],
                        extras=[], pending=[], source_text="原文",
                        report=ValidationReport(priority_overrides=overrides))
    plain = to_json(hw)
    assert plain["report"]["priority_overrides"][0]["llm"] == "high"
    back = from_json(plain)
    assert back.report.priority_overrides == overrides
    assert isinstance(back.report.priority_overrides[0], dict)
    # 显式的空列表表示「确实没有要求」，不能被 requirements 顶替
    hw2 = from_json({"items": [{"seq": 1, "requirements": ["a"], "requirements_all": []}]})
    assert hw2.items[0].requirements_all == []


def test_reads_poc_json_superset():
    """poc 产出的 JSON 必须能被新库读入，否则迁移就丢了历史数据。"""
    poc_shape = {"date": "2026-11-05", "items": [{"seq": 1, "subject": "数学",
                  "task": "练习册", "quantity": "P12-13", "requirements": [],
                  "priority": "high", "estimated_minutes": None, "type": "written",
                  "provenance": {"task": "exact"}}],
                 "extras": [], "unresolved": ["明天带美术材料"], "source_text": "原文"}
    hw = from_json(poc_shape)
    assert len(hw.pending) == 1
    assert hw.pending[0].text == "明天带美术材料"
    # 不卡枚举类型的话，下面三行在 poc 旧 JSON 上都是运行时崩点：
    # 尤其 p.reason.value——纯字符串没这个属性，而 CLI 和 confirm 打印 pending 时必读它
    assert hw.pending[0].reason is PendingReason.UNCOVERED
    assert hw.items[0].provenance["task"] is TraceLevel.VERBATIM
    assert hw.report is not None and hw.report.notes == []


def test_pending_and_unresolved_conflict_raises():
    """两个字段同时存在且内容不一致时不得静默合并。"""
    bad = {"date": "2026-11-05", "items": [], "extras": [], "source_text": "",
           "pending": [{"id": "x", "text": "甲", "reason": "uncovered",
                        "source_sentence": "", "related_seq": None}],
           "unresolved": ["乙"]}
    with pytest.raises(ValueError, match="冲突"):
        from_json(bad)


def test_legacy_poc_levels_are_all_known():
    """poc 写过的每个等级都得认得，否则历史 hw.json 读不进来。

    poc 写得出 exact/loose/weak/partial/missing/empty 六种，外加人工修正时写的
    manual（poc 的 --set 路径）。manual 的意思是「家长亲口定的」：poc 复用时
    跳过了溯源，所以它没有原文出处——按「已采信但不逐字命中」处理，
    既不进 pending 阻断，也别谎称是原文子串。
    """
    expected = {"exact": TraceLevel.VERBATIM, "loose": TraceLevel.NORMALIZED,
                "weak": TraceLevel.TOKENS_MATCH, "partial": TraceLevel.PARTIAL,
                "missing": TraceLevel.UNSOURCED, "empty": TraceLevel.VERBATIM,
                "manual": TraceLevel.NORMALIZED}
    data = {"items": [{"seq": 1, "task": "练习册",
                       "provenance": {n: n for n in expected}}]}
    prov = from_json(data).items[0].provenance
    for name, level in expected.items():
        assert prov[name] is level, name
    # 人工修正过的字段不进 pending，但要在 advisories 里留痕
    assert prov["manual"] in TRACE_ACCEPTED
    assert prov["manual"] in ADVISORY_LEVELS
