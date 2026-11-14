"""机械校验层（承重墙）。三条不变量，改任何一行前必须先证明没破坏它们：

1. 溯源：字段值必须在原文有出处，否则不采信。
2. 覆盖：原文每个实义片段必须被认领，否则回问家长。
3. 闸门：pending 非空 → 上层拒绝出图。

分级严宽的依据是代价：硬事实（科目/页码/数量/要求）错一个字就是错，零容错；
task 描述允许模型补动词（原文「练习册」→「完成练习册」），否则几乎每项都被拦，
产品就没法用了。放宽的边界永远是数字与字母词元——页码不许被补出来。
"""

from __future__ import annotations

import re
from dataclasses import replace

from homework_compass.errors import ExtractionError
from homework_compass.models import (
    ADVISORY_LEVELS, VALID_TYPES, HomeworkItem, ParsedHomework, PendingItem,
    PendingReason, SourceKind, TraceLevel, TraceRecord, ValidationReport,
    make_pending_id,
)
from homework_compass.parsing.provenance import FIELD_POLICY, Provenance, norm
from homework_compass.parsing.screening import is_junk_fragment
from homework_compass.parsing.segmentation import is_noise, split_chunks_with_context
from homework_compass.parsing.vocabulary import PRIORITY_MARKERS


def priority_of(blob: str) -> tuple[str, list[str]]:
    """优先级由程序按词表判定，模型给的一律覆盖。"""
    hits = [w for w in PRIORITY_MARKERS if w in (blob or "")]
    return ("high" if hits else "normal"), hits


def _record(report: ValidationReport, where: str, value: str, level: TraceLevel) -> None:
    rec = TraceRecord(where=where, value=value, level=level)
    report.traced.append(rec)
    if level in ADVISORY_LEVELS:
        report.advisories.append(rec)


def _texts(value: object) -> list[str]:
    """把字段值归一成非空字符串列表。

    模型偶尔把单个要求写成裸字符串；直接 for 循环会逐字符迭代，
    上图就变成「家」「长」「签」「字」一行一个字——而且每个字都有出处，
    溯源拦不住，只能在这里收口。
    """
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def _adopt_item(idx: int, raw_item: object, prov: Provenance,
                report: ValidationReport, demoted: list[str]) -> HomeworkItem | None:
    """返回可安全出图的项；找不到出处的部分降级进 demoted，绝不留在项里。"""
    if not isinstance(raw_item, dict):
        report.notes.append(f"第 {idx} 项不是对象，已忽略")
        return None
    subject = str(raw_item.get("subject") or "").strip()
    task = str(raw_item.get("task") or "").strip()
    quantity = str(raw_item.get("quantity") or "").strip()
    reqs = _texts(raw_item.get("requirements"))
    if not task:
        report.notes.append(f"第 {idx} 项 task 为空，已丢弃")
        return None

    t_pol = FIELD_POLICY["task"]
    t_level = prov.trace(task, policy=t_pol)
    _record(report, f"item{idx}.task", task, t_level)
    if t_level is TraceLevel.UNSOURCED:
        demoted.append(task + (f"（{quantity}）" if quantity else ""))
        return None

    q_level = prov.trace(quantity) if quantity else TraceLevel.VERBATIM
    _record(report, f"item{idx}.quantity", quantity, q_level)
    if quantity and q_level is TraceLevel.UNSOURCED:
        # 页码/数量零容错（spec §5.2）：没出处的数量必须置空，宁可缺一行也不印错。
        # 不在这里造 pending：原文那段（含真页码）会由覆盖率检查整段回问家长，
        # 一条光秃秃的数字反而让家长无从判断。
        report.notes.append(f"第 {idx} 项 quantity=“{quantity}”在原文找不到出处，已置空")
        quantity = ""

    s_level = prov.trace(subject) if subject else TraceLevel.VERBATIM
    if subject and s_level is TraceLevel.UNSOURCED:
        # 科目张冠李戴比漏一项更隐蔽：置空并回问，不把未证实的科目上图。
        _record(report, f"item{idx}.subject", subject, s_level)
        demoted.append(f"科目“{subject}”在原文找不到（对应任务：{task}）")
        subject = ""

    kept, lost = [], []
    for r in reqs:
        lvl = prov.trace(r)
        _record(report, f"item{idx}.requirements", r, lvl)
        (kept if lvl is not TraceLevel.UNSOURCED else lost).append(r)
    demoted.extend(lost)

    priority, signals = priority_of(" ".join([subject, task, quantity, *kept]))
    llm_priority = raw_item.get("priority")
    if llm_priority and llm_priority != priority:
        report.priority_overrides.append(
            {"where": f"item{idx}", "llm": str(llm_priority), "program": priority,
             "keywords": signals})

    itype = str(raw_item.get("type") or "written")
    if itype not in VALID_TYPES:
        report.notes.append(f"第 {idx} 项 type=“{itype}”不在枚举内，记为 unknown")
        itype = "unknown"

    # 模型爱把整句当 task、又把句尾要求单列一份，上图就印两遍。
    # 显示去重，但 requirements_all 保留全部——优先级判定不能因为去重漏掉「签字」。
    head = "".join([task, quantity])
    shown = [r for r in kept if norm(r) and norm(r) not in norm(head)]

    return HomeworkItem(
        seq=0, subject=subject, task=task, quantity=quantity,
        requirements=shown, requirements_all=kept, priority=priority,
        priority_signals=signals,
        estimated_minutes=raw_item.get("estimated_minutes"), type=itype,
        provenance={"task": t_level, "quantity": q_level, "subject": s_level},
    )


def _adopt_extras(parsed: dict, prov: Provenance, report: ValidationReport,
                  demoted: list[str]) -> list[str]:
    out = []
    for x in _texts(parsed.get("extras")):
        level = prov.trace(x)
        _record(report, "extras", x, level)
        (out if level is not TraceLevel.UNSOURCED else demoted).append(x)
    return out


def claimed_text(hw: ParsedHomework, *, include_pending: bool = False) -> str:
    """把所有「已被认领」的文本拼回一把尺子。

    覆盖率判定与销账判定必须用同一把尺子，否则会出现「程序认为已覆盖、
    家长却仍被卡在待确认」的死角。include_pending 在销账时必须关掉，
    否则待确认项会自己认领自己。
    """
    parts: list[str] = []
    for it in hw.items:
        parts.append("".join([it.subject, it.task, it.quantity, *it.requirements_all]))
        parts.extend([it.task, it.quantity, *it.requirements_all])
    parts.extend(hw.extras)
    if include_pending:
        parts.extend(p.text for p in hw.pending)
    parts.extend([hw.slogan, hw.student_name])
    return "；".join(p for p in parts if p)


def coverage_gaps(raw_text: str, hw: ParsedHomework) -> list[tuple[str, str]]:
    """原文里有、数据里没有的片段。返回 (片段, 所属整句)。"""
    prov = Provenance(claimed_text(hw))
    return [(c, f) for c, f in split_chunks_with_context(raw_text)
            if prov.trace(c) is TraceLevel.UNSOURCED]


def _related_seq(hw: ParsedHomework, fragment: str) -> int | None:
    fn = norm(fragment)
    for it in hw.items:
        if norm(it.task) and norm(it.task) in fn:
            return it.seq
    return None


def build_pending(hw: ParsedHomework, demoted: list[str], model_unresolved: list[str],
                  gaps: list[tuple[str, str]],
                  source_kind: SourceKind = SourceKind.TEXT) -> list[PendingItem]:
    """四路 pending 合流：模型自认含糊 + 无出处降级 + 原文遗漏 + OCR 强制。

    整段都是套话的一律自动丢弃并计入 stats——把「各位家长好」转成家长确认项
    会让产品根本没法用；但只要含一点实义内容就必须留下。
    """
    seen: dict[str, PendingItem] = {}
    dropped: list[str] = []

    def add(text: str, reason, sentence: str = "", seq: int | None = None) -> None:
        text = str(text).strip()
        if not text or is_noise(text):
            if text:
                dropped.append(text)
            return
        # 同一段文本可能既是模型自认含糊、又是覆盖率缺口：按文案去重（先到先得）。
        # 若按 id（含 reason）去重，家长会看到两条一模一样的待确认；
        # 销掉一条，另一条还卡着闸门。poc 也是按文案去重。
        if text in seen:
            return
        seen[text] = PendingItem(id=make_pending_id(reason, text), text=text,
                                 reason=reason, source_sentence=sentence,
                                 related_seq=seq)

    for u in model_unresolved:
        # 模型自认含糊的片段同样过一遍「像不像作业」的闸门：
        # 「敬」这种残字进 pending 只会打扰家长，也会让闸门永远关不上
        if is_junk_fragment(u):
            dropped.append(str(u).strip())
            continue
        add(u, PendingReason.AMBIGUOUS)
    for d in demoted:
        add(d, PendingReason.FABRICATED)
    for chunk, frag in gaps:
        add(chunk, PendingReason.UNCOVERED, frag, _related_seq(hw, frag))
    if source_kind is SourceKind.OCR:
        add("（本图来自 OCR 识别，请家长核对每一项）", PendingReason.OCR_UNVERIFIED)

    if dropped:
        hw.report.notes.append(
            f"已自动归入套话、不转家长确认 {len(dropped)} 段：" + " / ".join(dropped[:5]))
    # 审计面（spec §5.4）：覆盖率缺口如实列出。套话在分段层就被挡掉了，到不了这里；
    # 这里不依赖 pending 的过滤结果，保证 stats["uncovered"] 与
    # report.uncovered 永远对得上。
    hw.report.uncovered = [chunk for chunk, _ in gaps]
    hw.report.stats["auto_dropped_boilerplate"] = len(dropped)
    return list(seen.values())


def validate(raw_text: str, parsed: dict, *, date: str = "", name: str = "",
             source_kind: SourceKind = SourceKind.TEXT) -> ParsedHomework:
    if not isinstance(parsed, dict):
        raise ExtractionError("抽取结果不是对象，拒绝采信。")
    if parsed.get("items") is None:
        raise ExtractionError("抽取结果缺少 items 字段。")
    if not isinstance(parsed["items"], list):
        raise ExtractionError("items 必须是数组。")

    prov = Provenance(raw_text)
    report = ValidationReport(traced=[], advisories=[], uncovered=[],
                              priority_overrides=[], notes=[], stats={})
    demoted: list[str] = []
    items = []
    for idx, it in enumerate(parsed["items"], start=1):
        adopted = _adopt_item(idx, it, prov, report, demoted)
        if adopted is not None:
            items.append(adopted)
    for i, item in enumerate(items, start=1):
        item.seq = i
    extras = _adopt_extras(parsed, prov, report, demoted)

    hw = ParsedHomework(
        date=str(parsed.get("date") or date or ""),
        student_name=str(parsed.get("student_name") or name or ""),
        slogan=str(parsed.get("slogan") or ""), items=items, extras=extras,
        pending=[], source_text=raw_text, source_kind=source_kind, report=report,
    )
    report.stats.update({
        "items_safe": len(items),
        "items_dropped": len(parsed["items"]) - len(items),
        "unsourced": sum(1 for r in report.traced if r.level is TraceLevel.UNSOURCED),
        "advisories": len(report.advisories),
    })
    gaps = coverage_gaps(raw_text, hw)
    hw.pending = build_pending(hw, demoted,
                               [str(x) for x in (parsed.get("unresolved") or [])],
                               gaps, source_kind)
    report.stats["uncovered"] = len(gaps)
    return hw


EDITABLE_FIELDS: frozenset[str] = frozenset(
    {"subject", "task", "quantity", "requirements", "priority", "type"})


def drop_item(hw: ParsedHomework, seq: int) -> ParsedHomework:
    """家长删掉整条。照片识别出来的清单常有噪声行，逐字段清空太费事。

    删掉不等于「当它不存在」：重算覆盖率缺口，原文里没被别的项承接的整句
    照样回到 pending 回问家长——宁缺毋编。
    """
    target = next((i for i in hw.items if i.seq == seq), None)
    if target is None:
        raise ValueError(f"找不到第 {seq} 项")
    kept = [i for i in hw.items if i.seq != seq]
    for i, item in enumerate(kept, start=1):
        item.seq = i
    after = replace(hw, items=kept)
    after.pending = [p for p in hw.pending if is_covered(p.text, after)]
    gaps = coverage_gaps(after.source_text, after)
    for chunk, _frag in gaps:
        if is_noise(chunk) or any(p.text == chunk for p in after.pending):
            continue
        after.pending.append(PendingItem(
            id=make_pending_id(PendingReason.UNCOVERED, chunk), text=chunk,
            reason=PendingReason.UNCOVERED, source_sentence=_frag,
            related_seq=_related_seq(after, _frag)))
    after.report = replace(
        hw.report, notes=[*hw.report.notes, f"家长删除第 {seq} 项：{target.task}"],
        uncovered=[chunk for chunk, _ in gaps])
    return after


def is_covered(text: str, hw: ParsedHomework) -> bool:
    """这段文字是否已被数据本身承接。与提出它时用同一把尺子。"""
    return Provenance(claimed_text(hw, include_pending=False)).trace(
        text) is not TraceLevel.UNSOURCED


def correct(hw: ParsedHomework, seq: int, field: str, value: str) -> ParsedHomework:
    """家长改完字段后重新判定相关 pending：承接上了就销账，没承接就留着。

    家长是高于原文的事实来源，所以这里不再对家长输入做溯源拦截
    （否则「家长知道老师口误」这种情况就无解）；但修正动作要记进 notes 留痕。
    """
    if field not in EDITABLE_FIELDS:
        raise ValueError(f"字段 {field} 不在可改白名单 {sorted(EDITABLE_FIELDS)}")
    if field == "priority" and value not in ("high", "normal"):
        raise ValueError(f"priority 只能是 high/normal，收到 {value!r}")
    if field == "type" and value not in VALID_TYPES:
        raise ValueError(f"type 不在枚举内 {sorted(VALID_TYPES)}，收到 {value!r}")
    target = next((i for i in hw.items if i.seq == seq), None)
    if target is None:
        raise ValueError(f"找不到第 {seq} 项")

    new_target = replace(target)
    if field == "requirements":
        parts = [x.strip() for x in re.split(r"[，,、;；\n]", str(value)) if x.strip()]
        new_target.requirements = parts
        new_target.requirements_all = list(dict.fromkeys([*target.requirements_all, *parts]))
    else:
        setattr(new_target, field, value)
    if field in new_target.provenance:
        # 家长改出来的值可能根本不在原文里，审计数据不能继续谎称它逐字出自原文
        # （poc 的 manual 同义，见 models._LEGACY_LEVELS）；标黄留痕而不阻断。
        new_target.provenance = {**new_target.provenance, field: TraceLevel.NORMALIZED}

    if field != "priority":
        new_target.priority, new_target.priority_signals = priority_of(" ".join(
            [new_target.subject, new_target.task, new_target.quantity,
             *new_target.requirements_all]))

    items = [new_target if i.seq == seq else i for i in hw.items]
    after = replace(hw, items=items)
    after.pending = [p for p in hw.pending if not is_covered(p.text, after)]
    # 改对了的片段不再是覆盖率缺口，审计面必须跟着改；否则报告里永远挂着
    # 「原文有、数据没有」，家长会以为自己漏看了什么。
    gaps = coverage_gaps(after.source_text, after)
    after.report = replace(hw.report,
                           notes=[*hw.report.notes,
                                  f"第 {seq} 项 {field} 由家长修正为「{value}」"],
                           uncovered=[c for c, _ in gaps],
                           stats={**hw.report.stats, "uncovered": len(gaps)})
    return after


def dismiss(hw: ParsedHomework, pending_id: str) -> ParsedHomework:
    """家长明确表示「这条不上图」。只清这一条，且靠 id 而不是文案。"""
    target = next((p for p in hw.pending if p.id == pending_id), None)
    if target is None:
        raise ValueError(f"没有 id 为 {pending_id} 的待确认项（可能已销账）")
    after = replace(hw, pending=[p for p in hw.pending if p.id != pending_id])
    after.report = replace(hw.report,
                           notes=[*hw.report.notes, f"家长确认不纳入：{target.text}"])
    return after
