import pytest

from homework_compass.models import TraceLevel
from homework_compass.parsing.provenance import (
    FIELD_POLICY, Provenance, TracePolicy, strip_markers,
)

RAW = "📚今日作业：1.数学练习册P12-13；2.语文抄写本课生字2遍；3.英语听读打卡Unit3"


@pytest.fixture()
def prov():
    return Provenance(RAW)


def test_verbatim_substring(prov):
    assert prov.trace("抄写本课生字") is TraceLevel.VERBATIM


def test_dash_rewrite_is_tokens_match_not_unsourced(prov):
    """模型把 P12-13 写成 P12–P13 是规范化，不是杜撰。判错会把好数据扔进 pending。"""
    assert prov.trace("P12–P13") is TraceLevel.TOKENS_MATCH


def test_tokens_must_be_cut_from_raw_not_normalized(prov):
    """norm 会把 P12-13 粘成 p1213，若从 norm 串切词元就对不上。

    这条断言直接看词元集本身：只断言 trace 的结果会被 VERBATIM 分支抢跑，
    词元到底从哪切根本没被验到。
    """
    assert {"p", "12", "13"} <= prov.tokens   # 按分隔符切，不是粘成一坨
    assert "1213" not in prov.tokens          # norm 串里的粘连产物不得进词元集
    assert prov.trace("P12–P13") is TraceLevel.TOKENS_MATCH


def test_invented_word_is_unsourced(prov):
    assert prov.trace("用铅笔") is TraceLevel.UNSOURCED


def test_verb_completion_allowed_only_for_task(prov):
    """原文只写「练习册」，补成「完成练习册」应当放过——但仅限 task 档。"""
    loose = prov.trace("完成练习册", policy=TracePolicy.ALLOW_VERB_COMPLETION)
    strict = prov.trace("完成练习册", policy=TracePolicy.ZERO_TOLERANCE)
    assert loose is TraceLevel.PARTIAL
    assert strict is TraceLevel.UNSOURCED


def test_wrong_page_number_caught_even_in_lenient_policy(prov):
    """补动词可以，改页码不行：数字词元必须全部命中。"""
    assert prov.trace("完成练习册P14-15",
                      policy=TracePolicy.ALLOW_VERB_COMPLETION) is TraceLevel.UNSOURCED


def test_mostly_invented_task_caught_even_in_lenient_policy(prov):
    assert prov.trace("观察日记一篇",
                      policy=TracePolicy.ALLOW_VERB_COMPLETION) is TraceLevel.UNSOURCED


def test_empty_value_is_unsourced(prov):
    assert prov.trace("") is TraceLevel.UNSOURCED


def test_only_task_gets_the_lenient_policy():
    assert FIELD_POLICY["task"] is TracePolicy.ALLOW_VERB_COMPLETION
    for f in ("subject", "quantity", "requirements", "extras"):
        assert FIELD_POLICY[f] is TracePolicy.ZERO_TOLERANCE


def test_truncated_page_number_is_not_verbatim():
    """「P12」被写成「P1」是页码写错，不能因为它是原文子串就算逐字命中。

    norm 把 P12 压成 p12，于是 p12、p1 都是原文的子串；
    数字词元必须先全部命中原文，这道闸就是拦它们的。
    """
    prov = Provenance("数学练习册P12")
    assert prov.trace("P12") is TraceLevel.VERBATIM
    assert prov.trace("P1") is TraceLevel.UNSOURCED


def test_list_marker_does_not_legitimize_a_truncated_page():
    """原文的序号「1.」不是页码，不能让「P1」这种截断蒙混过关。

    序号里的数字也会进词元集：不去掉序号，截断的页码就成了命中。
    """
    prov = Provenance("1.数学练习册P12-13")
    assert prov.trace("P1") is TraceLevel.UNSOURCED
    assert prov.trace("P12-13") is TraceLevel.VERBATIM


def test_number_merge_is_not_treated_as_fabrication():
    """模型把 P12-13 写成 P1213 是去分隔符，不是杜撰。

    词元是「1213」，原文是「12」+「13」；按「必须原样出现」判，会把正确数据
    扔进 pending——那比漏判更烦人（spec §5.3）。
    """
    prov = Provenance("数学练习册P12-13")
    assert prov.trace("P1213") is TraceLevel.VERBATIM


def test_markers_are_stripped_but_page_numbers_are_not():
    """序号要剥，页码不能剥：「P12-13.」里的「13.」是页码的一部分。"""
    assert strip_markers("1.数学练习册P12-13；2、语文") == "数学练习册P12-13；语文"
    assert "P12-13." in strip_markers("数学练习册P12-13. 下节课")


def test_parenthetical_quantity_is_not_taken_for_a_marker():
    """「抄写生字（2）遍」里的 2 是数量，不是序号——剥掉就等于删掉真数字。

    剥错了词元集就少一个「2」，「抄写生字2遍」这条真作业反被判成杜撰，
    在 Task 6 里会变成一条阻断出图的 FABRICATED pending。
    """
    prov = Provenance("今日作业：1.语文抄写生字（2）遍")
    assert "2" in prov.tokens
    assert prov.trace("抄写生字2遍") is TraceLevel.VERBATIM


def test_marker_right_after_a_chinese_character_is_stripped():
    """「今天作业1.数学」的序号紧跟汉字，也得剥。

    不剥的话序号里的「1」会让截断的页码「P1」蒙混过关。
    """
    prov = Provenance("今天作业1.数学练习册P12-13")
    assert "1" not in prov.tokens
    assert prov.trace("P1") is TraceLevel.UNSOURCED
    assert prov.trace("P12-13") is TraceLevel.VERBATIM


def test_value_keeps_the_marker_verbatim():
    """模型逐字摘录原文时会带上「1.」，源侧与值侧得按同一套规则剥。"""
    prov = Provenance("今日作业：1.数学练习册P12-13")
    assert prov.trace("1.数学练习册P12-13") is TraceLevel.VERBATIM
    assert prov.trace("数学练习册P12-13") is TraceLevel.VERBATIM


def test_right_paren_marker_is_stripped():
    """无前括号的右括号形序号「1)数学」「1）数学」也得剥，否则「P1」又蒙混过关。

    这一支不能吃「(2)」：跟在括号后的数字一律当内容。
    """
    for raw in ("1)数学练习册P12-13", "1）数学练习册P12-13"):
        prov = Provenance(raw)
        assert "1" not in prov.tokens
        assert prov.trace("P1") is TraceLevel.UNSOURCED
        assert prov.trace("P12-13") is TraceLevel.VERBATIM
    assert "2" in Provenance("抄写生字(2)遍").tokens
    assert "2" in Provenance("抄写生字（2）遍").tokens
