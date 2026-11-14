from homework_compass.parsing.segmentation import (
    is_noise, split_chunks_with_context, split_fragments, strip_lead,
)


def test_greeting_with_modal_suffix_is_noise():
    """「各位家长好」比表里的「各位家长」多一个字，靠 startswith 才算得出来。"""
    assert is_noise("各位家长好！")
    assert is_noise("收到请回复，谢谢！")


def test_boilerplate_prefix_does_not_swallow_a_real_assignment():
    """危险方向的护栏：「收到书本后签字」开头就是套话「收到」，
       但它是一条真作业。前缀匹配一旦不设边界，过滤就会开始吞掉内容。"""
    assert not is_noise("收到书本后签字")
    assert not is_noise("谢谢家长配合，明天带彩泥")
    assert is_noise("各位家长好")          # 套话 + 一个语气字，仍然算套话


def test_deadline_is_never_noise():
    assert not is_noise("明天带美术材料：彩泥")
    assert not is_noise("今晚十点前完成")


def test_date_scaffold_header_is_noise_but_keeps_real_content():
    assert is_noise("今天（11月5日）的作业如下：")
    assert not is_noise("今天（11月5日）的作业如下：数学练习册P12")


def test_strip_lead_removes_decor_enum_and_connector():
    assert strip_lead("📚③英语：听读打卡") == "英语：听读打卡"
    assert strip_lead("1、背诗") == "背诗"
    assert strip_lead("另外明天记得穿校服") == "明天记得穿校服"


def test_connector_prefixed_fragment_not_double_reported():
    """poc 缺陷：原文「另外明天记得穿校服」，extras 已有「明天记得穿校服」，
       不剥连接词就会多报一条遗漏。"""
    assert split_fragments("另外明天记得穿校服") == ["明天记得穿校服"]


def test_chunk_carries_its_sentence_context():
    got = split_chunks_with_context("1.数学：完成练习册 P12-13，用铅笔，家长签字")
    assert ("完成练习册 P12-13" in [c for c, _ in got]) or any(
        "练习册" in c for c, _ in got)
    for chunk, frag in got:
        assert chunk in frag or norm_of(chunk) in norm_of(frag)


def norm_of(s: str) -> str:
    from homework_compass.parsing.provenance import norm
    return norm(s)


def test_pure_date_fragment_is_noise():
    """「11月6日」单独一行的日期是脚手架，不该变成待确认项；
    但「明天交」这类带动作的日期语义必须留着（宁缺毋编不能变成宁可漏报）。"""
    from homework_compass.parsing.segmentation import is_noise
    assert is_noise("11月6日")
    assert is_noise("（11月6日）")
    assert is_noise("今天")
    for keep in ("11月6日 交作业", "明天带美术材料", "下周三交观察日记"):
        assert not is_noise(keep), keep
