"""交互式销账：全项目唯一读取 tty 的模块。

它不知道任何「什么算杜撰」「什么算遗漏」的规则——那些在库里。
它只把 PendingItem 的 reason / source_sentence / related_seq 读给人看，
然后把人的选择转成 correct() / dismiss() 两次调用。

非 tty 时拒绝交互（spec §8.1）：输出结构化 JSON + 退出码 3。
「卡在一个没人能回答的 input() 上」是最坏的失败方式——AI 助手与 CI 都在这儿。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from homework_compass import pipeline
from homework_compass.cli.main import EXIT_OK, EXIT_PARSE_PENDING, EXIT_USAGE
from homework_compass.models import PendingReason
from homework_compass.parsing.validate import EDITABLE_FIELDS

REASON_CN = {
    PendingReason.FABRICATED: "无出处（疑似杜撰）",
    PendingReason.UNCOVERED: "疑似遗漏",
    PendingReason.AMBIGUOUS: "原文含糊，模型未归类",
    PendingReason.OCR_UNVERIFIED: "OCR 识别，需人工核对",
}


def run_confirm(hw_path: Path, *, stdin=None, stdout=None) -> int:
    stdin = stdin if stdin is not None else sys.stdin
    out = stdout if stdout is not None else sys.stdout
    hw_path = Path(hw_path)
    if not hw_path.is_file():
        # 裸 FileNotFoundError 会穿出 main() 变成 exit 1，破坏退出码契约
        print(f"文件不存在：{hw_path}", file=out)
        return EXIT_USAGE
    hw = pipeline.load_hw(hw_path)

    if not hw.pending:
        print("没有待确认项，可以直接 hw render。", file=out)
        return EXIT_OK

    if not stdin.isatty():
        # 非交互环境：把决策材料原样交出去，让人（或另一个 agent）来判。
        # 这里刻意不写盘——只读地报告状态，调用方才能安全重试。
        print(json.dumps({
            "interactive": False, "hw": str(hw_path),
            "pending": [{"id": p.id, "text": p.text, "reason": p.reason.value,
                         "source_sentence": p.source_sentence,
                         "related_seq": p.related_seq} for p in hw.pending],
            "hint": "用 hw parse --set / --resolve 处理，或在终端里运行 hw confirm",
        }, ensure_ascii=False, indent=2), file=out)
        return EXIT_PARSE_PENDING

    answers = _ask(hw, stdin, out)
    for seq, field, value in answers["edits"]:
        hw = pipeline.correct(hw, seq, field, value)
    for pid in answers["dismissed"]:
        # 前面的编辑可能已经把这条覆盖掉了（家长把别处的内容补进了字段）：
        # id 不存在不是错误，是已经解决。销账本身仍然只走 dismiss()。
        if any(p.id == pid for p in hw.pending):
            hw = pipeline.dismiss(hw, pid)
    pipeline.save_hw(hw, hw_path)
    if hw.pending:
        print(f"仍待确认 {len(hw.pending)} 项，已保存进度。", file=out)
        return EXIT_PARSE_PENDING
    print("全部已确认，可以 hw render。", file=out)
    return EXIT_OK


def _ask(hw, stdin, out) -> dict:
    edits, dismissed = [], []
    total = len(hw.pending)
    for n, p in enumerate(list(hw.pending), start=1):
        print(f"\n[{n}/{total}] {REASON_CN.get(p.reason, p.reason.value)}  「{p.text}」",
              file=out)
        if p.source_sentence:
            print(f"      出自：{p.source_sentence}", file=out)
        if p.related_seq:
            print(f"      关联：第 {p.related_seq} 项", file=out)
        print("   (e) 补进该项  (d) 不纳入  (s) 跳过保留  (q) 退出并保存", file=out)
        while True:
            print("   > ", end="", file=out, flush=True)
            # EOF 当作 q：没人回答时就保存已做的、停下，绝不在 readline 上空转
            choice = (stdin.readline() or "q").strip().lower()
            if choice == "q":
                return {"edits": edits, "dismissed": dismissed}
            if choice == "s":
                break
            if choice == "d":
                dismissed.append(p.id)
                break
            if choice == "e":
                seq = p.related_seq
                while not seq:
                    raw = stdin.readline()
                    if not raw:
                        # EOF。写成 `seq = int(raw) if raw.isdigit() else None`
                        # 会在这里死循环：空串不是数字，seq 永远为空。
                        break
                    if raw.strip().isdigit():
                        seq = int(raw.strip())
                if not seq:
                    print("   没有有效序号，跳过。", file=out)
                    break
                print("   写入哪个字段（默认 task）：", end="", file=out, flush=True)
                field = (stdin.readline() or "task").strip() or "task"
                if field not in EDITABLE_FIELDS:
                    print(f"   字段 {field} 不在白名单 {sorted(EDITABLE_FIELDS)}，跳过。",
                          file=out)
                    break
                print("   新值：", end="", file=out, flush=True)
                value = (stdin.readline() or "").strip()
                if value:
                    edits.append((seq, field, value))
                break
            print("   看不懂这个选择，请用 e / d / s / q。", file=out)
    return {"edits": edits, "dismissed": dismissed}
