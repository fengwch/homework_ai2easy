from homework_compass.parsing import vocabulary as v


def test_deadline_words_are_not_connectors():
    """「另外」怎么写都不是任务，但「明天」是截止时间，吞掉就是丢数据。"""
    for word in ("明天", "今天", "后天"):
        assert word not in v.CONNECTORS


def test_deadline_words_are_not_boilerplate():
    """BOILERPLATE 是会真正丢内容的表，截止时间绝不能进去。

    上一条只锁了 CONNECTORS；套话表才是噪声判定真正用的那张，
    「明天」若被加进去，作业里那句「明天带美术材料」就没了。
    """
    assert not ({"今天", "明天", "后天"} & v.BOILERPLATE)
    assert not (set(v.PRIORITY_MARKERS) & v.BOILERPLATE)


def test_task_verbs_are_not_priority_markers():
    """poc 实测缺陷：「准备好彩泥和剪刀」因「准备」被判高优，是误判。"""
    assert "准备" not in v.PRIORITY_MARKERS
    assert "重点" not in v.PRIORITY_MARKERS


def test_every_marker_carries_a_reason():
    """词表就是产品行为，没有存在理由的条目不许进表。"""
    assert all(reason.strip() for reason in v.PRIORITY_MARKERS.values())


def test_markers_split_into_two_kinds():
    events = {w for w, why in v.PRIORITY_MARKERS.items() if why.startswith("事件")}
    deadlines = {w for w, why in v.PRIORITY_MARKERS.items() if why.startswith("截止")}
    assert {"签字", "打卡", "背诵"} <= events
    assert {"明天"} <= deadlines


def test_boilerplate_lookup_is_length_sorted_desc():
    got = v.boilerplate_by_len()
    assert got == sorted(got, key=len, reverse=True)
