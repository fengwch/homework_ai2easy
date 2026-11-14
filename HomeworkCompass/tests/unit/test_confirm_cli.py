import io
import json

from homework_compass.cli.confirm import run_confirm
from homework_compass.parsing.extract import StubExtractor
from homework_compass.pipeline import load_hw, parse_homework, save_hw

# 恰好吃出 1 条 pending（家长签字），且 related_seq=1：
# 「(d) 不纳入一次就清空」「(e) 不用再问第几项」这两条测试名才立得住。
RAW_ONE = "1.数学：完成练习册P12-13，家长签字"
# 两条 pending 且 related_seq=None：用来走「先问第几项」的分支
RAW_TWO = "1.数学：完成练习册P12-13\n2.明天带美术材料：彩泥"


def _tty(text: str) -> io.StringIO:
    s = io.StringIO(text)
    s.isatty = lambda: True            # type: ignore[assignment]
    return s


def _hw_for(path, raw, items):
    hw = parse_homework(raw, extractor=StubExtractor(
        {"items": items, "extras": [], "unresolved": []}), date="2026-11-06")
    save_hw(hw, path)
    return hw


def pending_hw(tmp_path):
    p = tmp_path / "hw.json"
    hw = _hw_for(p, RAW_ONE, [{"subject": "数学", "task": "完成练习册",
                               "quantity": "P12-13"}])
    assert [x.text for x in hw.pending] == ["家长签字"]
    return hw, p


def two_pending_hw(tmp_path):
    p = tmp_path / "hw.json"
    hw = _hw_for(p, RAW_TWO, [{"subject": "数学", "task": "完成练习册",
                               "quantity": "P12-13"}])
    assert {x.text for x in hw.pending} == {"明天带美术材料", "彩泥"}
    return hw, p


def test_non_tty_refuses_interaction_and_emits_json(tmp_path, capsys):
    """AI 助手/CI 里绝不能卡在 input() 上——结构化输出 + 退出码才是可用形态。"""
    _, p = pending_hw(tmp_path)
    before = p.read_text(encoding="utf-8")
    assert run_confirm(p, stdin=io.StringIO("")) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["pending"] and payload["interactive"] is False
    assert p.read_text(encoding="utf-8") == before     # 非 tty 不写盘


def test_dismiss_path_clears_pending(tmp_path):
    _, p = pending_hw(tmp_path)
    assert run_confirm(p, stdin=_tty("d\n")) == 0
    assert load_hw(p).pending == []


def test_edit_path_uses_library_correct(tmp_path, monkeypatch):
    """销账必须走库：CLI 用替身数出来的调用次数，就是「它没自己实现规则」的证据。"""
    _, p = pending_hw(tmp_path)
    import homework_compass.cli.confirm as cf

    real = cf.pipeline.correct
    calls = []
    monkeypatch.setattr(cf.pipeline, "correct",
                        lambda *a, **kw: calls.append(a) or real(*a, **kw))
    assert run_confirm(p, stdin=_tty("e\nrequirements\n家长签字\n")) == 0
    assert calls and calls[0][1] == 1 and calls[0][2] == "requirements"
    assert load_hw(p).pending == []


def test_edit_prompts_for_seq_when_pending_has_no_related_item(tmp_path, monkeypatch):
    _, p = two_pending_hw(tmp_path)
    import homework_compass.cli.confirm as cf

    seen = []
    real = cf.pipeline.correct
    monkeypatch.setattr(cf.pipeline, "correct",
                        lambda *a, **kw: seen.append(a[1]) or real(*a, **kw))
    # e -> 问第几项(1) -> 字段 requirements -> 新值
    assert run_confirm(p, stdin=_tty("e\n1\nrequirements\n家长签字\nq\n")) == 3
    assert seen == [1]                  # 「第几项」真的被问到了，且用上了答案


def test_eof_at_seq_prompt_skips_instead_of_spinning(tmp_path, monkeypatch):
    """EOF 时 `raw.isdigit()` 永远为假：没这道保护就是死循环。"""
    _, p = two_pending_hw(tmp_path)
    import homework_compass.cli.confirm as cf

    calls = []
    real = cf.pipeline.correct
    monkeypatch.setattr(cf.pipeline, "correct",
                        lambda *a, **kw: calls.append(a) or real(*a, **kw))
    assert run_confirm(p, stdin=_tty("e\n")) == 3
    assert calls == []                  # 没编号就不猜，直接跳过


def test_bad_choice_reprompts_instead_of_crashing(tmp_path):
    _, p = pending_hw(tmp_path)
    assert run_confirm(p, stdin=_tty("x\nd\n")) == 0
    assert load_hw(p).pending == []


def test_stale_dismiss_after_edit_does_not_crash(tmp_path, monkeypatch):
    """用户先把两项都补进第 1 项、再对第 2 项选 d：那条 id 已经不存在了。

    销账只能走 dismiss()，但「id 已经不在了」不是错误，是编辑已经把它解决了。
    """
    _, p = two_pending_hw(tmp_path)
    import homework_compass.cli.confirm as cf

    real = cf.pipeline.correct
    monkeypatch.setattr(cf.pipeline, "correct",
                        lambda *a, **kw: real(*a, **kw))
    # 第 1 条：补进第 1 项的 task；第 2 条：选 d（此时它已被上面的编辑覆盖）
    stdin = _tty("e\n1\ntask\n明天带美术材料：彩泥\nd\n")
    assert run_confirm(p, stdin=stdin) == 0
    assert load_hw(p).pending == []


def test_skip_keeps_pending_and_exits_three(tmp_path):
    _, p = pending_hw(tmp_path)
    assert run_confirm(p, stdin=_tty("s\n")) == 3
    assert load_hw(p).pending


def test_quit_saves_progress(tmp_path):
    hw, p = pending_hw(tmp_path)
    assert run_confirm(p, stdin=_tty("q\n")) == 3
    assert len(load_hw(p).pending) == len(hw.pending)


def test_prompt_shows_reason_context_and_related_seq(tmp_path, capsys):
    _, p = pending_hw(tmp_path)
    run_confirm(p, stdin=_tty("q\n"))
    out = capsys.readouterr().out
    assert "疑似遗漏" in out and "出自" in out and "关联：第 1 项" in out


def test_nothing_to_confirm_is_immediately_ok(tmp_path):
    p = tmp_path / "hw.json"
    _hw_for(p, "1.数学：练习册P12-13", [{"subject": "数学", "task": "练习册",
                                          "quantity": "P12-13"}])
    assert run_confirm(p, stdin=io.StringIO("")) == 0


def test_missing_hw_json_is_usage_error(tmp_path):
    """文件不存在要落回 4；裸 FileNotFoundError 会穿出 main() 变成 exit 1。"""
    assert run_confirm(tmp_path / "nope.json", stdin=io.StringIO("")) == 4
