"""中枢数据类型。本文件不含业务分支，只含结构与其 JSON 序列化。

字段名是上游方案文档定义的 schema 的超集：新增字段可以，改名或删除不行，
否则 poc 期间产出的 JSON 与历史 hw.json 会读不出来。

另有一条不变量：**pending 条目的 `text` 必须非空**。`from_json` 会拒收空 text
（报错比静默丢弃强），内存里若造出空 text 的 `PendingItem`，写出去的文件自己
读不回来——所以构造 pending 时就别让文案为空。
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class TraceLevel(str, Enum):
    VERBATIM = "verbatim"          # 去标点后是原文子串
    NORMALIZED = "normalized"      # 连接符/写法被改写
    TOKENS_MATCH = "tokens_match"  # 词元全命中、顺序不成立
    PARTIAL = "partial"            # 仅 task 允许：数字全中 + 汉字重合≥0.6
    UNSOURCED = "unsourced"        # 无出处 → 拒绝采信


TRACE_ACCEPTED = frozenset({TraceLevel.VERBATIM, TraceLevel.NORMALIZED,
                            TraceLevel.TOKENS_MATCH, TraceLevel.PARTIAL})
ADVISORY_LEVELS = TRACE_ACCEPTED - {TraceLevel.VERBATIM}

# HomeworkItem.type 的取值白名单。模型偶尔会自创「考试」「手工」这类值，
# 校验层把它改写成 unknown 并留痕，而不是原样放行到排版层。
VALID_TYPES: frozenset[str] = frozenset({"written", "oral", "reading", "checkin", "material"})


class PendingReason(str, Enum):
    FABRICATED = "fabricated"
    UNCOVERED = "uncovered"
    AMBIGUOUS = "ambiguous"
    OCR_UNVERIFIED = "ocr_unverified"


class SourceKind(str, Enum):
    TEXT = "text"
    OCR = "ocr"
    VOICE = "voice"
    REUSE = "reuse"


def make_pending_id(reason: PendingReason, text: str) -> str:
    """稳定标识。销账靠它而不是靠文案子串匹配——家长改一个字就不该对不上。"""
    digest = hashlib.sha1(f"{reason.value}\x1f{text}".encode()).hexdigest()[:8]
    return f"{reason.value[:3]}-{digest}"


@dataclass(slots=True)
class TraceRecord:
    where: str                 # 形如 "item3.task"
    value: str
    level: TraceLevel


@dataclass(slots=True)
class HomeworkItem:
    seq: int
    subject: str
    task: str
    quantity: str
    requirements: list[str]        # 上图显示的要求（已去除与 task 重复者）
    requirements_all: list[str]    # 校验通过的全部要求（供优先级判定与审计）
    priority: str = "normal"
    priority_signals: list[str] = field(default_factory=list)
    estimated_minutes: int | None = None
    type: str = "written"
    provenance: dict[str, TraceLevel] = field(default_factory=dict)


@dataclass(slots=True)
class PendingItem:
    id: str                    # 稳定标识，销账靠它，不靠文案匹配
    text: str                  # 给家长看的原文片段
    reason: PendingReason
    source_sentence: str = ""  # 出自原文哪一句
    related_seq: int | None = None  # 关联到第几项，供 CLI 提示"补进第 4 项"


@dataclass(slots=True)
class ValidationReport:
    """溯源与覆盖的完整审计结果。只用于展示与排错，不作为出图闸门依据。"""

    traced: list[TraceRecord] = field(default_factory=list)
    advisories: list[TraceRecord] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)
    priority_overrides: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedHomework:
    date: str
    student_name: str
    slogan: str
    items: list[HomeworkItem]
    extras: list[str]
    pending: list[PendingItem]
    source_text: str = ""
    # 通关奖励文案。空字符串 = 家长选择不显示奖励框；非空才画「通关奖励：xxx」
    reward: str = ""
    source_kind: SourceKind = SourceKind.TEXT
    # 永不为 None：poc 旧 JSON 没有这个字段，读进来一律给空报告，
    # 于是 correct()/dismiss() 可以直接 hw.report.notes，不必处处防 None
    report: ValidationReport = field(default_factory=ValidationReport)


@dataclass(slots=True)
class RenderIssue:
    zone: str
    text: str
    reason: str


@dataclass(slots=True)
class RenderResult:
    path: Path
    width: int
    height: int
    dpi: tuple[int, int]
    issues: list[RenderIssue] = field(default_factory=list)
    used_placeholder: bool = False


# legacy 是 poc 时代写下的等级名。manual 是 poc 的 --set 路径写的：
# 家长亲口改过的字段，poc 复用时跳过溯源，所以它根本没有原文出处。
# 归到 normalized：采信但不阻断（不进 pending），同时进 advisories 留痕；
# 归到 verbatim 会谎称「是原文子串」，还会被 ADVISORY_LEVELS 排除掉。
_LEGACY_LEVELS = {"exact": "verbatim", "loose": "normalized", "weak": "tokens_match",
                  "partial": "partial", "missing": "unsourced", "empty": "verbatim",
                  "manual": "normalized"}


def _enum(cls, value, where: str):
    """把 JSON 里的字符串还原成枚举；不认的就报错，不自作主张当成默认值。"""
    try:
        return cls(value)
    except ValueError:
        raise ValueError(f"{where} 读到未知值 {value!r}，可选：{[m.value for m in cls]}") from None


def _plain(value):
    """递归把枚举换成 .value，让 asdict 的结果能被 json.dumps 写出去。

    str 混入型枚举「看起来已经是字符串」，但 type() 仍是 Enum；下游一旦把它
    当普通字符串处理（写 JSON、比对、再读回来）就会出错，所以在此显式拆掉。
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def to_json(hw: ParsedHomework) -> dict:
    data = _plain(asdict(hw))
    # 上游 schema 保留 unresolved 字段名：spec §4 要求它是 pending 的文本投影，
    # 写出去供旧工具消费（旧工具只认这个键）；读取时仍以 pending 为准
    data["unresolved"] = [p.text for p in hw.pending]
    return data


def from_json(data: dict) -> ParsedHomework:
    pending_raw = data.get("pending")
    legacy_raw = data.get("unresolved")
    pending = []
    for p in pending_raw or []:
        reason = _enum(PendingReason, p.get("reason"), "pending.reason")
        # 归一化只做一次：id 由文案派生，unresolved 投影也是文案，
        # 两边不一致会让往返读误判成「冲突」
        text = str(p.get("text") or "").strip()
        if not text:
            # id 是从 reason+text 派生的，缺了可以自己补；text 缺了没法补，
            # 只能报错——让它以 KeyError 冒出去会变成无提示的 traceback
            raise ValueError("pending 条目缺 text，无法向家长展示待确认内容")
        pending.append(PendingItem(id=p.get("id") or make_pending_id(reason, text),
                                   text=text, reason=reason,
                                   source_sentence=p.get("source_sentence", ""),
                                   related_seq=p.get("related_seq")))
    legacy = [str(x).strip() for x in (legacy_raw or [])]
    if pending and legacy:
        # 静默合并会让「到底哪条待确认」变成猜，宁可报错
        # 两边用同一套归一化：pending 侧也要 strip，否则 to_json 写出的
        # unresolved 投影与 pending 不一致，往返读会误报「冲突」
        if {p.text.strip() for p in pending} != set(legacy):
            raise ValueError("pending 与 unresolved 内容冲突，请只保留一个来源")
    elif legacy and not pending:
        pending = [PendingItem(id=make_pending_id(PendingReason.UNCOVERED, t), text=t,
                               reason=PendingReason.UNCOVERED, source_sentence="",
                               related_seq=None) for t in legacy]

    items = []
    for raw in data.get("items") or []:
        items.append(HomeworkItem(
            seq=raw.get("seq") or len(items) + 1,
            subject=raw.get("subject", ""), task=raw.get("task", ""),
            quantity=raw.get("quantity", ""),
            requirements=[str(x) for x in raw.get("requirements") or []],
            # poc 只写 requirements；requirements_all 缺失时退回它，去重交给校验层。
            # 用「键是否存在」而不是真值判断：显式的 [] 表示「确实没有要求」，
            # 不能被 requirements 覆盖
            requirements_all=[str(x) for x in (raw["requirements_all"]
                                               if "requirements_all" in raw
                                               else raw.get("requirements") or [])],
            priority=raw.get("priority", "normal"),
            priority_signals=[str(x) for x in raw.get("priority_signals") or []],
            estimated_minutes=raw.get("estimated_minutes"),
            type=raw.get("type", "written"),
            provenance={k: _enum(TraceLevel, _LEGACY_LEVELS.get(v, v), f"item{len(items) + 1}.provenance.{k}")
                        for k, v in (raw.get("provenance") or {}).items()}))

    report_raw = data.get("report")

    def _records(rows):
        return [TraceRecord(where=r.get("where", ""), value=r.get("value", ""),
                            level=_enum(TraceLevel, _LEGACY_LEVELS.get(r.get("level"),
                                                                       r.get("level")),
                                        "report.level"))
                for r in rows or []]

    report = ValidationReport(
        traced=_records(report_raw.get("traced")),
        advisories=_records(report_raw.get("advisories")),
        uncovered=[str(x) for x in report_raw.get("uncovered") or []],
        # 声明类型是 list[dict]：校验层写进来的是 {"where","llm","program","keywords"}，
        # 强转 str 会把审计信息变成 Python repr，读回来就没法当审计数据用了
        priority_overrides=[dict(x) if isinstance(x, dict) else {"raw": str(x)}
                            for x in (report_raw.get("priority_overrides") or [])],
        notes=[str(x) for x in report_raw.get("notes") or []],
        stats=dict(report_raw.get("stats") or {}),
    ) if report_raw else ValidationReport()

    kind = data.get("source_kind")
    return ParsedHomework(
        date=data.get("date", ""), student_name=data.get("student_name", ""),
        slogan=data.get("slogan", ""), items=items,
        extras=[str(x) for x in data.get("extras") or []], pending=pending,
        source_text=data.get("source_text", ""),
        reward=str(data.get("reward") or ""),
        source_kind=_enum(SourceKind, kind, "source_kind") if kind else SourceKind.TEXT,
        report=report)
