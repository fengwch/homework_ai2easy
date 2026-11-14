from pathlib import Path

import pytest

from homework_compass.parsing.extract import LlmExtractor
from homework_compass.parsing.validate import validate

pytestmark = pytest.mark.network
RAW2 = Path(__file__).resolve().parents[1] / "fixtures" / "raw2.txt"


def test_real_llm_extract_of_raw2_is_clean():
    """真实模型 + 机械校验：poc 实测 5 项全部可溯源、0 pending。

    priority 预期与 poc 不同：美术项原文只写了「准备好彩泥和剪刀」，
    poc 因关键词「准备」判高优，新版已从 PRIORITY_MARKERS 移除（spec §5.5 规则 2）。
    """
    raw = RAW2.read_text(encoding="utf-8")
    hw = validate(raw, LlmExtractor()(raw, name="小宇"))
    assert len(hw.items) == 5
    assert hw.pending == []
    assert [i.priority for i in hw.items] == ["high", "normal", "high", "normal", "normal"]
