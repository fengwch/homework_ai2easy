import json
import sys
from dataclasses import replace

import pytest

from homework_compass.cli.main import (
    EXIT_OK, EXIT_PARSE_PENDING, EXIT_PENDING, EXIT_REMOTE, EXIT_USAGE, main,
)
from homework_compass.config import load_config
from homework_compass.models import SourceKind

RAW = ("各位家长好！今天（11月5日）的作业如下：\n"
       "①语文：《静夜思》背诵并默写，家长签字\n②数学：练习册第12-13页\n"
       "收到请回复，谢谢！")
BARE = "1.数学：完成练习册P12-13\n2.明天带美术材料：彩泥"
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
needs_macos_fonts = pytest.mark.skipif(sys.platform != "darwin",
                                       reason="候选表是 macOS 系统字体路径")


@pytest.fixture()
def raw(tmp_path):
    p = tmp_path / "raw.txt"
    p.write_text(RAW, encoding="utf-8")
    return p


@needs_macos_fonts
def test_parse_then_render_end_to_end(tmp_path, raw, capsys):
    hw = tmp_path / "hw.json"
    assert main(["parse", "--file", str(raw), "--name", "小宇", "--offline",
                 "--out", str(hw)]) == EXIT_OK
    assert main(["render", str(hw), "--out", str(tmp_path / "out")]) == EXIT_OK
    png = next((tmp_path / "out").glob("*.png"))
    assert png.is_file()
    assert "2480x3508" in capsys.readouterr().out


def test_ocr_parse_exits_three_and_still_writes_json(tmp_path, monkeypatch):
    """照片这条路必须过家长确认：即便 --offline，OCR 结果也带 pending、退出码 3。

    退出码 3 与「hw.json 已落盘」必须同时成立，否则 `hw confirm hw.json`
    没有文件可接——离线解析器从不让 pending 非空，这条只能走 OCR 路径构造。
    """
    from homework_compass.cli import main as cli_main

    seen = {}

    def fake_ocr(image, *, model=None):
        seen["model"] = model
        return "1.数学：练习册P12-13", SourceKind.OCR

    monkeypatch.setattr(cli_main.pipeline, "text_from_image", fake_ocr)
    hw = tmp_path / "hw.json"
    code = main(["parse", "--image", str(tmp_path / "board.jpg"), "--offline",
                 "--out", str(hw)])
    assert code == EXIT_PARSE_PENDING
    data = json.loads(hw.read_text(encoding="utf-8"))
    assert [p["reason"] for p in data["pending"]] == ["ocr_unverified"]
    assert seen["model"] == "qwen-vl-ocr"      # 走 config.ocr_model，不是 --text-model


def test_render_with_pending_exits_two_and_leaves_no_file(tmp_path):
    hw = tmp_path / "hw.json"
    hw.write_text(json.dumps({"date": "2026-11-06", "items": [], "extras": [],
                              "pending": [{"id": "unc-1", "text": "带跳绳",
                                           "reason": "uncovered",
                                           "source_sentence": "明天带跳绳",
                                           "related_seq": None}],
                              "source_text": "明天带跳绳", "source_kind": "text"},
                             ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out"
    assert main(["render", str(hw), "--out", str(out)]) == EXIT_PENDING
    assert not out.exists() or list(out.glob("*.png")) == []


def test_bad_set_expression_is_usage_error(tmp_path):
    assert main(["parse", "--text", BARE, "--offline", "--out",
                 str(tmp_path / "hw.json"), "--set", "1.quantity"]) == EXIT_USAGE


def test_non_whitelist_field_is_usage_error(tmp_path):
    assert main(["parse", "--text", BARE, "--offline", "--out",
                 str(tmp_path / "hw.json"), "--set", "1.seq=9"]) == EXIT_USAGE


def test_dismiss_by_ref_accepts_partial_quote(tmp_path):
    """家长只记得几个字也要能销账（poc 行为），但命中多条时必须报错而不是挑第一条。

    这里直接测 `_dismiss_by_ref` 而不走 `main([... , "--resolve"])`：离线解析器把
    每个非套话句都当成作业项认领了，所以 `--offline` 路径下 pending 恒为空，
    `--resolve` 根本无法从命令行抵达。手工造一份带 pending 的 hw.json 才能构造出它。
    """
    from homework_compass.cli.main import _dismiss_by_ref
    from homework_compass.pipeline import load_hw

    p = tmp_path / "hw.json"
    p.write_text(json.dumps({
        "date": "2026-11-06", "items": [], "extras": [], "source_text": "原文",
        "source_kind": "text",
        "pending": [{"id": "unc-1", "text": "明天带美术材料：彩泥", "reason": "uncovered",
                     "source_sentence": "另外明天带美术材料：彩泥", "related_seq": None},
                    {"id": "unc-2", "text": "带跳绳", "reason": "uncovered",
                     "source_sentence": "", "related_seq": None}]},
        ensure_ascii=False), encoding="utf-8")
    hw = load_hw(p)
    assert [x.id for x in _dismiss_by_ref(hw, "美术").pending] == ["unc-2"]
    with pytest.raises(ValueError, match="无法定位"):
        _dismiss_by_ref(hw, "带")        # 两条都含「带」，不许猜第一条


def test_unknown_skeleton_is_usage_error(tmp_path):
    hw = tmp_path / "hw.json"
    hw.write_text(json.dumps({"date": "x", "items": [], "extras": [], "pending": [],
                              "source_text": "", "source_kind": "text"}), encoding="utf-8")
    assert main(["render", str(hw), "--skeleton", "nope",
                 "--out", str(tmp_path)]) == EXIT_USAGE


def test_bad_flag_exits_four_not_two():
    """命令行写错绝不能返回 2。2 的含义是「有 pending，要家长看」，
    而 argparse 出错时默认 `sys.exit(2)`，会让调用方把拼错参数当成一次正常拒绘。

    三个 case 各挡一条路（均已在 Python 3.13 上实测）：子命令内部的坏旗、
    未知子命令、缺必填位置参数——后两类走的是父 parser 的 error()，
    只修子 parser 拦不住。（坏旗 `--nope` 会被 argparse 先当成缺少 `hw` 位置参数，
    两者都该映射到 4，所以不断言具体报错文本。）
    """
    assert main(["render", "--nope"]) == EXIT_USAGE
    assert main(["nope"]) == EXIT_USAGE
    assert main(["render"]) == EXIT_USAGE


def test_zones_and_prompt_are_free(capsys):
    assert main(["zones"]) == EXIT_OK
    assert main(["prompt", "--skeleton", "quest-map"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "station-1" in out and "框内不得绘制任何文字" in out


def test_api_error_maps_to_five(tmp_path, monkeypatch, raw):
    """构造 extractor 时就会 401，所以补丁必须打在 cli.main 的命名空间上：
    CLI 是自己 `LlmExtractor(...)` 的，打 `pipeline` 上的同名属性打不到。"""
    from homework_compass.errors import ApiError
    from homework_compass.cli import main as cli_main

    def boom(*a, **kw):
        raise ApiError("HTTP 401：API Key 无效，检查环境变量")

    monkeypatch.setattr(cli_main, "LlmExtractor", boom)
    assert main(["parse", "--file", str(raw),
                 "--out", str(tmp_path / "hw.json")]) == EXIT_REMOTE


def test_malformed_payload_maps_to_five(tmp_path, monkeypatch):
    """模型返回的不是对象：这是上游坏了（5），不是用户参数写错（4）。

    映射成 4 会让脚本以为改改命令就能重试，白白重放一次可能计费的请求。"""
    from homework_compass.cli import main as cli_main

    class Garbage:
        def __init__(self, *, model=None):
            pass

        def __call__(self, raw_text, *, date="", name=""):
            return []                      # 不是 dict，校验层会抛 ExtractionError

    monkeypatch.setattr(cli_main, "LlmExtractor", Garbage)
    assert main(["parse", "--text", BARE,
                 "--out", str(tmp_path / "hw.json")]) == EXIT_REMOTE


def test_missing_input_file_is_usage_error(tmp_path):
    assert main(["parse", "--file", str(tmp_path / "nope.txt"), "--out",
                 str(tmp_path / "hw.json")]) == EXIT_USAGE


def test_missing_hw_json_is_usage_error(tmp_path):
    """render 的输入文件不存在也要落回 4：裸 FileNotFoundError 会变成 exit 1 + traceback。"""
    assert main(["render", str(tmp_path / "nope.json"),
                 "--out", str(tmp_path / "out")]) == EXIT_USAGE


def test_text_model_flag_reaches_the_online_extractor(tmp_path, monkeypatch):
    from homework_compass.cli import main as cli_main

    seen = {}

    class Spy:
        def __init__(self, *, model=None):
            seen["model"] = model

        def __call__(self, raw_text, *, date="", name=""):
            return {"items": [{"subject": "数学", "task": "练习册",
                               "quantity": "P12-13"}],
                    "extras": [], "unresolved": []}

    monkeypatch.setattr(cli_main, "LlmExtractor", Spy)
    code = main(["parse", "--text", "1.数学：练习册P12-13", "--text-model",
                 "qwen-max", "--out", str(tmp_path / "hw.json")])
    assert code == EXIT_OK and seen["model"] == "qwen-max"


def test_offline_never_constructs_the_online_extractor(tmp_path, monkeypatch):
    """默认路径不花钱：--offline 时连 LlmExtractor 都不许构造。"""
    from homework_compass.cli import main as cli_main

    def boom(*a, **kw):
        raise AssertionError("--offline 不许构造 LlmExtractor")

    monkeypatch.setattr(cli_main, "LlmExtractor", boom)
    assert main(["parse", "--text", BARE, "--offline",
                 "--out", str(tmp_path / "hw.json")]) == EXIT_OK


@needs_macos_fonts
def test_config_fonts_are_threaded_into_render(tmp_path, monkeypatch):
    """spec §6.4.1：配置里的候选表要真的到达 render，否则它就是死配置。"""
    from homework_compass.cli import main as cli_main

    cfg = replace(load_config(), fonts=(ARIAL,))
    monkeypatch.setattr(cli_main, "load_config", lambda *a, **kw: cfg)
    hw = tmp_path / "hw.json"
    hw.write_text(json.dumps({"date": "2026-11-06", "items": [], "extras": [],
                              "pending": [], "source_text": "",
                              "source_kind": "text"}), encoding="utf-8")
    # Arial 过不了字形覆盖探针 -> FontError -> 5；fonts 没传下去的话这里会成功出图
    assert main(["render", str(hw), "--out", str(tmp_path / "out")]) == EXIT_REMOTE
