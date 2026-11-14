"""CLI 适配层：解析参数、调用 pipeline、把结果与问题清单读给人看。

这里不许出现任何校验或销账逻辑——它们都属于库。CLI 的全部特权是知道退出码。

退出码是对外契约（spec §8.3），脚本与 AI 助手都靠它分支：
0 成功 / 2 有 pending 拒绝出图 / 3 解析产生 pending / 4 参数或白名单错误 / 5 接口或字体错误。
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from homework_compass import pipeline
from homework_compass.config import load_config, load_dotenv_default
from homework_compass.errors import (
    ApiError, ConfigError, ExtractionError, FontError, LayoutError, NeedsConfirmation,
)
from homework_compass.layout.skeleton import build_prompt, get_skeleton, zones_report
from homework_compass.models import SourceKind
from homework_compass.parsing.extract import LlmExtractor, NaiveExtractor
from homework_compass.parsing.provenance import norm
from homework_compass.parsing.validate import EDITABLE_FIELDS

EXIT_OK, EXIT_PENDING, EXIT_PARSE_PENDING, EXIT_USAGE, EXIT_REMOTE = 0, 2, 3, 4, 5

PLACEHOLDER_NOTICE = "！这是排版预览（占位底图），不是可打印成品。真实底图请用 --base。"


class _Parser(argparse.ArgumentParser):
    """把 argparse 的「出错就 sys.exit(2)」改成抛 ValueError。

    退出码 2 在本项目里已经被「有 pending、拒绘」占了。argparse 遇到拼错
    参数、缺必填项时会自己 sys.exit(2)，直穿 `main()` 冒到进程外：调用方拿到
    一个「正常拒绘」的码，而实际上一张图都没试过。重写成 ValueError 后，
    统一由 `main()` 的 except 分支翻译成 EXIT_USAGE。
    """

    def error(self, message: str):
        raise ValueError(message)


def build_parser() -> argparse.ArgumentParser:
    ap = _Parser(prog="hw", description="每日作业目标生成器")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse", help="作业原文 -> hw.json（抽取 + 机械校验）")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", type=Path)
    src.add_argument("--text")
    src.add_argument("--image", type=Path, help="板书照片，先 OCR 再解析（强制家长确认）")
    p.add_argument("--name", default="")
    p.add_argument("--date", default=dt.date.today().isoformat())
    p.add_argument("--offline", action="store_true", help="用离线兜底解析器，不花钱不联网")
    p.add_argument("--text-model", default=None, help="覆盖 config 的文本模型")
    p.add_argument("--ocr-model", default=None, help="覆盖 config 的 OCR 模型")
    p.add_argument("--set", action="append", default=[], metavar="N.FIELD=值",
                   help=f"修正字段，白名单 {sorted(EDITABLE_FIELDS)}")
    p.add_argument("--resolve", action="append", default=[], metavar="id或文本",
                   help="声明某条待确认项不纳入图")
    p.add_argument("--out", type=Path, default=Path("hw.json"))

    c = sub.add_parser("confirm", help="逐条处理 pending（只在 tty 上交互）")
    c.add_argument("hw", type=Path)

    r = sub.add_parser("render", help="hw.json -> A4 300dpi PNG")
    r.add_argument("hw", type=Path)
    r.add_argument("--skeleton", default=None)
    r.add_argument("--skin", default=None)
    r.add_argument("--base", type=Path, help="本地底图；不传则用占位图（预览）")
    r.add_argument("--panel-alpha", type=int, default=190)
    r.add_argument("--out", type=Path, default=None)

    z = sub.add_parser("zones", help="打印坐标契约（不花钱）")
    z.add_argument("--skeleton", default="quest-map")

    q = sub.add_parser("prompt", help="打印生图提示词（本版只打印，不调用）")
    q.add_argument("--skeleton", default="quest-map")
    q.add_argument("--skin", default="dinosaur")
    return ap


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        # 顺序不能倒：load_config 里的环境变量覆盖是读 os.environ 实现的，
        # 先 load_config 会把 .env 中的值全部漏掉。
        load_dotenv_default()
        cfg = load_config()

        # 四个子命令全在 try 里。zones/prompt 不花钱不等于不会错：
        # 把它们放在 try 外面，一个未知骨架名就是裸 KeyError + traceback。
        if args.cmd == "zones":
            sk = get_skeleton(args.skeleton)
            print(f"骨架：{sk.cn_name}｜A4 2480x3508 @300dpi")
            print(zones_report(sk))
            return EXIT_OK
        if args.cmd == "prompt":
            print(build_prompt(get_skeleton(args.skeleton), args.skin))
            return EXIT_OK
        if args.cmd == "parse":
            return _parse(args, cfg)
        if args.cmd == "render":
            return _render(args, cfg)
        if args.cmd == "confirm":
            from homework_compass.cli.confirm import run_confirm
            return run_confirm(args.hw)
    except NeedsConfirmation as e:
        print(str(e), file=sys.stderr)
        return EXIT_PENDING
    except (ApiError, ExtractionError, FontError) as e:
        # 模型返回垃圾与 401 是同一档：上游坏了，改命令行重试没有意义。
        print(f"接口/字体错误：{e}", file=sys.stderr)
        return EXIT_REMOTE
    except (ConfigError, LayoutError, ValueError) as e:
        print(f"用法或数据错误：{e}", file=sys.stderr)
        return EXIT_USAGE
    return EXIT_USAGE


def _parse(args, cfg) -> int:
    kind = SourceKind.TEXT
    if args.image:
        # OCR 模型来自 config.ocr_model（--ocr-model 可覆盖）；--text-model 管的是
        # 文本抽取，两条链路可以配不同模型。
        raw_text, kind = pipeline.text_from_image(
            args.image, model=args.ocr_model or cfg.ocr_model)
        print(f"OCR 文本：{raw_text[:120]}", file=sys.stderr)
    elif args.file:
        if not args.file.is_file():
            print(f"文件不存在：{args.file}", file=sys.stderr)
            return EXIT_USAGE
        raw_text = args.file.read_text(encoding="utf-8")
    else:
        raw_text = args.text or ""

    hw = pipeline.parse_homework(raw_text, extractor=pick_extractor(args, cfg),
                                 date=args.date, name=args.name or cfg.name,
                                 source_kind=kind)
    for (seq, field), value in _sets(args.set):
        hw = pipeline.correct(hw, seq, field, value)
    for ref in args.resolve:
        hw = _dismiss_by_ref(hw, ref)
    pipeline.save_hw(hw, args.out)
    print(f"写入：{args.out}｜可出图 {len(hw.items)} 项｜待确认 {len(hw.pending)} 项")
    for p in hw.pending:
        print(f"  ? [{p.reason.value}] {p.text}"
              + (f"　（出自「{p.source_sentence}」）" if p.source_sentence else ""))
    return EXIT_PARSE_PENDING if hw.pending else EXIT_OK


def pick_extractor(args, cfg):
    """默认离线；只有明确不 --offline 时才注入在线 extractor（会花钱）。"""
    if args.offline:
        return NaiveExtractor()
    return LlmExtractor(model=args.text_model or cfg.text_model)


def _sets(exprs: list[str]):
    for expr in exprs:
        m = re.match(r"^(\d+)\.(\w+)=(.*)$", expr.strip())
        if not m:
            raise ValueError(f"--set 语法错误：{expr}（应为 序号.字段=值）")
        seq, field, value = int(m.group(1)), m.group(2), m.group(3)
        if field not in EDITABLE_FIELDS:
            raise ValueError(f"字段 {field} 不在可改白名单 {sorted(EDITABLE_FIELDS)}")
        yield (seq, field), value


def _dismiss_by_ref(hw, ref: str):
    """允许用 pending id 销账，也允许复述它看到的文本（家长不该被要求抄 id）。"""
    target = next((p for p in hw.pending if p.id == ref), None)
    if target is None:
        rn = norm(ref)
        cands = [p for p in hw.pending
                 if rn and (rn in norm(p.text)
                            or (p.source_sentence and rn in norm(p.source_sentence)))]
        if len(cands) != 1:
            raise ValueError(f"无法定位待确认项「{ref}」（匹配 {len(cands)} 条，请用 id）")
        target = cands[0]
    return pipeline.dismiss(hw, target.id)


def _render(args, cfg) -> int:
    if not args.hw.is_file():
        # 不先查就 read_text：FileNotFoundError/Oserror 不在下面的 except 里，
        # 会变成 exit 1 + traceback，而脚本只认 0/2/3/4/5 这套契约。
        print(f"文件不存在：{args.hw}", file=sys.stderr)
        return EXIT_USAGE
    hw = pipeline.load_hw(args.hw)
    result = pipeline.render(hw, skeleton=args.skeleton or cfg.default_skeleton,
                             skin=args.skin or cfg.default_skin, base=args.base,
                             out_dir=args.out or cfg.out_dir,
                             panel_alpha=args.panel_alpha, fonts=cfg.fonts)
    print(f"成品：{result.path}  ({result.width}x{result.height} @300dpi)")
    if result.used_placeholder:
        print(PLACEHOLDER_NOTICE, file=sys.stderr)
    if result.issues:
        print("排版问题（不静默放行）：", file=sys.stderr)
        for i in result.issues:
            print(f"  ! [{i.zone}] {i.reason} —— “{i.text}”", file=sys.stderr)
    else:
        print("排版无问题。")
    return EXIT_OK
