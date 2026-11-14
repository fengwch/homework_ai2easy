# HomeworkCompass 核心包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个 Python 库 `homework_compass`（作业原文 → 机械校验 → A4 排版图）与命令行工具 `hw`，实现"零杜撰、零遗漏、有歧义必拦"。

**Architecture:** 双层合成：文字全部由 Pillow 绘制，坐标契约同时驱动生图提示词与文字落位。抽取层可注入（LLM / 离线兜底 / 测试桩），其后紧跟一道与上游无关的机械校验；`pending` 非空即拒绝出图。

**Tech Stack:** Python 3.13、Pillow 12.x、pytest 9.x；HTTP 走标准库 `urllib`；配置读 stdlib `tomllib`。

**Spec:** `docs/superpowers/specs/2026-11-06-homework-compass-core-design.md` — 本计划逐节实现该文档，执行时两个文件都要读。

## Global Constraints

每个任务的隐含要求都包含本节，值从 spec 逐字抄录：

- 运行时依赖**只有 Pillow**；开发依赖只有 pytest。禁止引入 pydantic / click / typer / rich / requests。
- 包布局为 `src/homework_compass/`，任何模块**不得**出现 `sys.path.insert`。
- 模块依赖单向：`cli/ → pipeline → parsing.*, layout.* → models, errors`；`parsing.*` 与 `layout.*` 互不依赖；`llm_client` 只被 `parsing.extract` 依赖。
- A4 竖版像素 `2480×3508`，DPI `300`，页边距 `≥10mm`，正文 `≥14pt` 等效、字号下限 `12pt`（触底即报问题，不静默截断）。
- 底图**必须先超分到 2480×3508 再绘文字**，顺序不可颠倒。
- `DASHSCOPE_API_KEY` 只从环境变量读取；`config.py` 中不存在读取该字段的代码路径。
- 待确认项非空 → 禁止出图，抛 `NeedsConfirmation`。
- 任何校验问题一律向上冒泡并打印，**绝不静默放行**。
- 网络测试打 `-m network`，默认不跑。
- 提交信息用中文，前缀遵循 `docs:` / `feat:` / `test:` / `chore:`。

---

## 文件结构（先定边界，再拆任务）

```
pyproject.toml
src/homework_compass/
├── __init__.py           # 只 re-export public API，内部实现不对外
├── models.py             # 全部数据类型与枚举，无逻辑分支
├── errors.py             # 异常层级
├── config.py             # config.toml / profile.toml / 环境变量优先级
├── llm_client.py         # DashScope chat 传输 + 鉴权 + 可操作错误信息
├── pipeline.py           # public 编排：parse_homework / correct / dismiss / render
├── parsing/
│   ├── provenance.py     # norm / Provenance / TracePolicy / FIELD_POLICY
│   ├── segmentation.py   # is_noise / split_fragments / split_chunks_with_context
│   ├── vocabulary.py     # BOILERPLATE / CONNECTORS / PRIORITY_MARKERS
│   ├── validate.py       # 溯源 + 覆盖两道校验 → ParsedHomework
│   └── extract.py        # Extractor 协议 + LlmExtractor + NaiveExtractor + StubExtractor
├── layout/
│   ├── skeleton.py       # Zone / Skeleton / quest_map / build_prompt / zones_report
│   ├── fonts.py          # 字体解析 + 字形覆盖探针
│   └── compose.py        # 超分、折行、字号收缩、绘制、RenderIssue
└── cli/
    ├── main.py           # argparse 适配层 + 退出码
    └── confirm.py        # 交互式销账（全项目唯一读 tty 处）
tests/
├── unit/            按模块一一对应
├── integration/     全链路（StubExtractor，零网络）
├── regression/      poc 四个真实 bug
└── fixtures/        raw1.txt / raw2.txt（从 poc 的 source_text 抽取）
```

划分原则：`provenance`（怎么判定出处）与 `segmentation`（怎么切原文）分开，因为 poc 里两者混在一个文件里导致改动互相牵连；`vocabulary` 单独成文件因为它是产品行为。

---

## Task 1: 包骨架与安装态

**Files:**
- Create: `pyproject.toml`
- Create: `src/homework_compass/__init__.py`
- Create: `src/homework_compass/errors.py`
- Create: `tests/unit/test_package_imports.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: 无
- Produces: 异常层级 `HomeworkError` / `ExtractionError` / `NeedsConfirmation` / `LayoutError` / `FontError` / `ApiError`，后续所有任务直接 `from homework_compass.errors import ...`

- [ ] **Step 1: 先把 poc 基线入库**（spec §10 第 2 步；不入库则后续平价校验无法重现、删除动作也成不了真实提交）

```bash
git status --short          # 必须确认 poc/.env 不在待提交列表里
git add poc/
git commit -m "chore: poc 基线快照，仅作平价比对用，将被删除"
```

Expected: `git status` 输出中**不含** `poc/.env`。若出现，立刻停止并修 `.gitignore`，凭证一旦入库就必须轮换。

- [ ] **Step 2: 写 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "homework-compass"
version = "0.1.0"
description = "每日作业目标生成器：解析 + 机械校验 + A4 排版"
requires-python = ">=3.13"
dependencies = ["Pillow>=12.0"]

[project.optional-dependencies]
dev = ["pytest>=9.0"]

[project.scripts]
hw = "homework_compass.cli.main:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["network: 需要真实 API，默认不跑"]
addopts = "-m 'not network'"
```

- [ ] **Step 3: 写异常层级**

`src/homework_compass/errors.py`：

```python
"""异常层级。设计原则：错误信息必须可操作，禁止静默放行。"""


class HomeworkError(Exception):
    """所有本项目异常的基类。"""


class ExtractionError(HomeworkError):
    """抽取失败：模型没返回合法结构，或原文为空。"""


class NeedsConfirmation(HomeworkError):
    """存在阻断型待确认项，拒绝出图。"""


class LayoutError(HomeworkError):
    """版面约束不满足：项数超骨架留白、骨架边距不达标等。"""


class FontError(HomeworkError):
    """找不到中文字体，或字体不覆盖所需汉字。"""


class ApiError(HomeworkError):
    """远端接口错误。message 必须包含下一步动作，不得只说「失败」。"""
```

- [ ] **Step 4: 写 `__init__.py` 占位（Task 15 的 pipeline 一节才填 API 导出）**

```python
"""每日作业目标生成器核心包。

public API 在 pipeline 落地时（Task 15）填进来，届时只从本文件 re-export。
"""

__all__: list[str] = []
```

- [ ] **Step 5: 写导入冒烟测试**

`tests/unit/test_package_imports.py`：

```python
import pytest

from homework_compass import errors


@pytest.mark.parametrize("name", [
    "HomeworkError", "ExtractionError", "NeedsConfirmation",
    "LayoutError", "FontError", "ApiError",
])
def test_exception_hierarchy(name):
    exc = getattr(errors, name)
    assert issubclass(exc, errors.HomeworkError)


def test_no_sys_path_hacks_in_source():
    """src/ 布局的意义就是消灭 sys.path.insert，这里把它变成硬约束。"""
    from pathlib import Path
    root = Path(errors.__file__).parent
    offenders = [p for p in root.rglob("*.py") if "sys.path.insert" in p.read_text()]
    assert offenders == []
```

- [ ] **Step 6: 安装并跑测试**

Run: `python3 -m pip install -e ".[dev]" && python3 -m pytest -q`
Expected: `7 passed`（`test_exception_hierarchy` 参数化 6 个异常名，加 `test_no_sys_path_hacks_in_source`），且收集阶段无 `ModuleNotFoundError`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/homework_compass/ tests/unit/test_package_imports.py
git commit -m "feat: 初始化 homework_compass 包骨架与异常层级"
```

---

## Task 2: 数据模型与 JSON 兼容

**Files:**
- Create: `src/homework_compass/models.py`
- Create: `tests/unit/test_models.py`

**Interfaces:**
- Consumes: 无（本文件只含结构与序列化；`from_json` 的数据错误一律抛 `ValueError`，Task 16 的 CLI 已把 `ValueError` 归入 `EXIT_USAGE`，所以这里不必再包一层 `HomeworkError`）
- Produces:

```python
class TraceLevel(str, Enum): VERBATIM NORMALIZED TOKENS_MATCH PARTIAL UNSOURCED
class PendingReason(str, Enum): FABRICATED UNCOVERED AMBIGUOUS OCR_UNVERIFIED
class SourceKind(str, Enum): TEXT OCR VOICE REUSE
TRACE_ACCEPTED: frozenset[TraceLevel]        # 前四个，UNSOURCED 不在内
ADVISORY_LEVELS: frozenset[TraceLevel]       # NORMALIZED TOKENS_MATCH PARTIAL

@dataclass(slots=True) class TraceRecord: where: str; value: str; level: TraceLevel
@dataclass(slots=True) class HomeworkItem: seq subject task quantity requirements
      requirements_all priority priority_signals estimated_minutes type provenance
@dataclass(slots=True) class PendingItem: id text reason source_sentence related_seq
@dataclass(slots=True) class ValidationReport: traced advisories uncovered
      priority_overrides notes stats
@dataclass(slots=True) class ParsedHomework: date student_name slogan items extras
      pending source_text source_kind report
@dataclass(slots=True) class RenderIssue: zone text reason
@dataclass(slots=True) class RenderResult: path width height dpi issues used_placeholder

def make_pending_id(reason: PendingReason, text: str) -> str
def to_json(hw: ParsedHomework) -> dict
def from_json(data: dict) -> ParsedHomework
```

- [ ] **Step 1: 写失败测试**

`tests/unit/test_models.py`：

```python
import pytest

from homework_compass.models import (
    ADVISORY_LEVELS, HomeworkItem, ParsedHomework, PendingItem, PendingReason,
    SourceKind, TraceLevel, TRACE_ACCEPTED, ValidationReport, from_json,
    make_pending_id, to_json,
)


def test_unsourced_is_not_accepted_but_partial_is():
    assert TraceLevel.UNSOURCED not in TRACE_ACCEPTED
    assert TraceLevel.PARTIAL in TRACE_ACCEPTED


def test_advisory_levels_never_block():
    """规范化判定只提示不阻断，否则 P12-13→P12–P13 会卡死整个流程。"""
    assert ADVISORY_LEVELS == {TraceLevel.NORMALIZED, TraceLevel.TOKENS_MATCH, TraceLevel.PARTIAL}


def test_pending_id_is_stable_and_text_sensitive():
    a = make_pending_id(PendingReason.UNCOVERED, "明天带美术材料")
    b = make_pending_id(PendingReason.UNCOVERED, "明天带美术材料")
    c = make_pending_id(PendingReason.UNCOVERED, "明天带美术材料：彩泥")
    assert a == b and a != c


def test_roundtrip_preserves_pending():
    """pending 必须带真内容：空列表 roundtrip 什么都验不到。"""
    p = PendingItem(id=make_pending_id(PendingReason.UNCOVERED, "明天带美术材料"),
                    text="明天带美术材料", reason=PendingReason.UNCOVERED,
                    source_sentence="", related_seq=None)
    it = HomeworkItem(seq=1, subject="数学", task="练习册", quantity="P12-13",
                      requirements=["用铅笔"], requirements_all=["用铅笔"],
                      priority="normal", priority_signals=[], estimated_minutes=None,
                      type="written", provenance={"task": TraceLevel.VERBATIM})
    hw = ParsedHomework(date="2026-11-06", student_name="小宇", slogan="", items=[it],
                        extras=[], pending=[p], source_text="原文",
                        source_kind=SourceKind.TEXT)
    plain = to_json(hw)
    # type is str 而不是 isinstance：混入 str 的枚举 isinstance 也过关，那正是陷阱
    assert type(plain["pending"][0]["reason"]) is str
    # unresolved 是 pending 的文本投影，旧工具只认这个键（spec §4）
    assert plain["unresolved"] == ["明天带美术材料"]
    # provenance 里的枚举在 asdict 后仍是 Enum，靠 _plain 拆掉
    assert type(plain["items"][0]["provenance"]["task"]) is str
    assert plain["items"][0]["provenance"]["task"] == "verbatim"
    back = from_json(plain)
    assert back.source_text == "原文"
    assert back.pending == [p]
    assert back.pending[0].reason is PendingReason.UNCOVERED
    assert back.source_kind is SourceKind.TEXT
    assert back.items[0].provenance["task"] is TraceLevel.VERBATIM
    assert back.items[0].requirements_all == ["用铅笔"]


def test_roundtrip_survives_padded_pending_text():
    """pending 文案带空白时，往返读必须成功——否则 save→load 会把 hw.json 变成废纸。

    to_json 写的 unresolved 是 pending 文案的投影，两边归一化不一致时
    from_json 会误判成「冲突」，CLI 会报一句莫名其妙的话。
    """
    hw = from_json({"pending": [{"text": "  甲  ", "reason": "uncovered"}]})
    assert hw.pending[0].text == "甲"
    back = from_json(to_json(hw))
    assert back.pending[0].text == "甲"
    assert back.pending[0].id == hw.pending[0].id


def test_audit_dicts_and_empty_requirements_survive_roundtrip():
    """priority_overrides 是 list[dict]；显式的 requirements_all=[] 不得被 requirements 覆盖。"""
    overrides = [{"where": "item1.task", "llm": "high", "program": "normal"}]
    hw = ParsedHomework(date="2026-11-06", student_name="小宇", slogan="", items=[],
                        extras=[], pending=[], source_text="原文",
                        report=ValidationReport(priority_overrides=overrides))
    plain = to_json(hw)
    assert plain["report"]["priority_overrides"][0]["llm"] == "high"
    back = from_json(plain)
    assert back.report.priority_overrides == overrides
    assert isinstance(back.report.priority_overrides[0], dict)
    # 显式的空列表表示「确实没有要求」，不能被 requirements 顶替
    hw2 = from_json({"items": [{"seq": 1, "requirements": ["a"], "requirements_all": []}]})
    assert hw2.items[0].requirements_all == []


def test_reads_poc_json_superset():
    """poc 产出的 JSON 必须能被新库读入，否则迁移就丢了历史数据。"""
    poc_shape = {"date": "2026-11-05", "items": [{"seq": 1, "subject": "数学",
                  "task": "练习册", "quantity": "P12-13", "requirements": [],
                  "priority": "high", "estimated_minutes": None, "type": "written",
                  "provenance": {"task": "exact"}}],
                 "extras": [], "unresolved": ["明天带美术材料"], "source_text": "原文"}
    hw = from_json(poc_shape)
    assert len(hw.pending) == 1
    assert hw.pending[0].text == "明天带美术材料"
    # 不卡枚举类型的话，下面三行在 poc 旧 JSON 上都是运行时崩点：
    # 尤其 p.reason.value——纯字符串没这个属性，而 CLI 和 confirm 打印 pending 时必读它
    assert hw.pending[0].reason is PendingReason.UNCOVERED
    assert hw.items[0].provenance["task"] is TraceLevel.VERBATIM
    assert hw.report is not None and hw.report.notes == []


def test_pending_and_unresolved_conflict_raises():
    """两个字段同时存在且内容不一致时不得静默合并。"""
    bad = {"date": "2026-11-05", "items": [], "extras": [], "source_text": "",
           "pending": [{"id": "x", "text": "甲", "reason": "uncovered",
                        "source_sentence": "", "related_seq": None}],
           "unresolved": ["乙"]}
    with pytest.raises(ValueError, match="冲突"):
        from_json(bad)


def test_legacy_poc_levels_are_all_known():
    """poc 写过的每个等级都得认得，否则历史 hw.json 读不进来。

    poc 写得出 exact/loose/weak/partial/missing/empty 六种，外加人工修正时写的
    manual（poc 的 --set 路径）。manual 的意思是「家长亲口定的」：poc 复用时
    跳过了溯源，所以它没有原文出处——按「已采信但不逐字命中」处理，
    既不进 pending 阻断，也别谎称是原文子串。
    """
    expected = {"exact": TraceLevel.VERBATIM, "loose": TraceLevel.NORMALIZED,
                "weak": TraceLevel.TOKENS_MATCH, "partial": TraceLevel.PARTIAL,
                "missing": TraceLevel.UNSOURCED, "empty": TraceLevel.VERBATIM,
                "manual": TraceLevel.NORMALIZED}
    data = {"items": [{"seq": 1, "task": "练习册",
                       "provenance": {n: n for n in expected}}]}
    prov = from_json(data).items[0].provenance
    for name, level in expected.items():
        assert prov[name] is level, name
    # 人工修正过的字段不进 pending，但要在 advisories 里留痕
    assert prov["manual"] in TRACE_ACCEPTED
    assert prov["manual"] in ADVISORY_LEVELS
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_models.py -q`
Expected: `ModuleNotFoundError: No module named 'homework_compass.models'`

- [ ] **Step 3: 实现 models.py**

`src/homework_compass/models.py` — 关键片段（数据类字段按上面 Interfaces 表逐一写出）：

```python
"""中枢数据类型。本文件不含业务分支，只含结构与其 JSON 序列化。

字段名是上游方案文档定义的 schema 的超集：新增字段可以，改名或删除不行，
否则 poc 期间产出的 JSON 与历史 hw.json 会读不出来。
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from enum import Enum


class TraceLevel(str, Enum):
    VERBATIM = "verbatim"          # 去标点后是原文子串
    NORMALIZED = "normalized"      # 连接符/写法被改写
    TOKENS_MATCH = "tokens_match"  # 词元全命中、顺序不成立
    PARTIAL = "partial"            # 仅 task 允许：数字全中 + 汉字重合≥0.6
    UNSOURCED = "unsourced"        # 无出处 → 拒绝采信


TRACE_ACCEPTED = frozenset({TraceLevel.VERBATIM, TraceLevel.NORMALIZED,
                            TraceLevel.TOKENS_MATCH, TraceLevel.PARTIAL})
ADVISORY_LEVELS = TRACE_ACCEPTED - {TraceLevel.VERBATIM}


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
```

`to_json` / `from_json` 的兼容规则必须照写。`from_json` 对**缺字段必须宽容**（poc 产物没有 `report`、`source_kind`、`requirements_all`、`priority_signals`，CLI 手写的中间态也可能只有一半），缺的一律给默认值；但对**内容冲突必须严格**（下面 `pending` 与 `unresolved` 那条）。

两条必须守住的不变量，写成代码而不是注释：

1. **枚举出 JSON 必须还原**。JSON 里存的是字符串，而 `str` 混入型 Enum “看起来能直接比”是个陷阱：`R.UNCOVERED == "uncovered"` 为真、`hash` 也相等（实测 Python 3.13，混入 str 后走的是 str 的 `__hash__`，按值而非按名），所以查字典不报错——但 `p.reason.value` 会 `AttributeError: 'str' object has no attribute 'value'`，而这正是 `cli/main.py` 和 `cli/confirm.py` 打印每条 pending 时必走的一行。`TraceRecord.level`、`HomeworkItem.provenance` 的值、`ParsedHomework.source_kind` 同理。还原用 `cls(value)`，不认的字符串一律抛错，不静默兜底。
2. **`report` 永不为 None**。poc 旧 JSON 没有 `report` 字段，读进来一律给空 `ValidationReport()`；这样 `correct()` / `dismiss()` 可以直接 `hw.report.notes`，不必处处防 None。`ValidationReport` 六个字段全部带 `default_factory`，所以 `ValidationReport()` 合法。

```python
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
        source_kind=_enum(SourceKind, kind, "source_kind") if kind else SourceKind.TEXT,
        report=report)
```

`to_json` 就是 `asdict(hw)` 再把枚举转成 `.value`（str 混入型靠 `json.dumps` 也能写对，但 `asdict` 后的 `provenance` 字典值是 Enum，为了 `from_json` 能直接读，统一显式写成 `str(v)` 更稳）。

此外 **`to_json` 必须额外写出 `unresolved`**：spec §4 明确「`unresolved` 仅作为 `pending` 的文本投影写出，供旧工具消费」，而旧工具只认这个键。`pending` 与 `unresolved` 同时存在时读取以 `pending` 为准；两边文案都经过同一套归一化（去首尾空白），所以 `from_json(to_json(hw))` 永远不会误报「冲突」。

```python
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
```

注意：`ValidationReport.priority_overrides` 的声明类型是 `list[dict]`（校验层写进来的是
`{"where","llm","program","keywords"}`），`from_json` 不得用 `str(x)` 强转——那会把
审计信息变成 Python repr 字符串，读回来就当不了审计数据用。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_models.py -q`
Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/models.py tests/unit/test_models.py
git commit -m "feat: 添加中枢数据模型与 poc JSON 兼容读取"
```

---

## Task 3: 词表（产品行为，不是实现细节）

**Files:**
- Create: `src/homework_compass/parsing/vocabulary.py`
- Create: `src/homework_compass/parsing/__init__.py`
- Create: `tests/unit/test_vocabulary.py`

**Interfaces:**
- Consumes: 无
- Produces: `BOILERPLATE: frozenset[str]`、`CONNECTORS: frozenset[str]`、`PRIORITY_MARKERS: dict[str, str]`（词 → 为什么它意味着重要）、`boilerplate_by_len() -> list[str]`

- [ ] **Step 1: 写失败测试——把三条硬规则变成断言**

`tests/unit/test_vocabulary.py`：

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_vocabulary.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 vocabulary.py**

```python
"""三张词表。它们决定「什么该问家长」和「什么算重要」，属于产品行为。

改动任何一行都要先想清楚会不会静默吞掉真实作业内容——
宁可多问家长一次，不可少报一项作业。
"""

from __future__ import annotations

BOILERPLATE: frozenset[str] = frozenset({
    "今日作业", "今天的作业", "今日任务", "作业", "温馨提示", "各位家长",
    "家长朋友们", "家长们", "孩子们", "收到", "谢谢", "好的", "以上", "备注",
    "加油", "收到请回复", "请签字", "已阅", "辛苦", "晚安",
})

# 只收「怎么写都不是作业」的词。今天/明天/后天是截止时间，绝不在内。
CONNECTORS: frozenset[str] = frozenset({
    "另外", "此外", "还有", "然后", "接着", "以及", "并且", "同时", "其它", "其他",
    "补充", "注意", "提醒",
})

# 词 → 为什么它意味着重要。前缀「事件」「截止」用于测试分类。
PRIORITY_MARKERS: dict[str, str] = {
    "签字": "事件：需要家长当场参与，漏了等于没完成",
    "打卡": "事件：需要 APP 侧留痕，错过时间就补不了",
    "背诵": "事件：口头任务最容易被孩子跳过",
    "默写": "事件：同背诵，需家长核对",
    "测验": "事件：有明确日期且影响复习安排",
    "需带": "事件：实物遗漏直接影响明天上课",
    "自带": "事件：同上",
    "带来": "事件：同上",
    "明天": "截止：涉及次日交付，属于易失事项",
    "后天": "截止：同上",
    # spec §5.5 规则 2 把截止时间定义为「明天/后天/周X」，周X 就是一整周七天；
    # 少列几天会造成「周三前交」不报警、「周一前交」报警的怪现象
    "周一": "截止：指定星期的交付日",
    "周二": "截止：指定星期的交付日",
    "周三": "截止：指定星期的交付日",
    "周四": "截止：指定星期的交付日",
    "周五": "截止：指定星期的交付日",
    "周六": "截止：指定星期的交付日",
    "周日": "截止：指定星期的交付日",
}


def boilerplate_by_len() -> list[str]:
    """按长度倒序返回，供调用方逐个长词优先匹配。

    调用方必须按这个顺序匹配，否则「收到请回复」会被「收到」抢先吃掉——
    这个函数只负责给顺序，不代替调用方做匹配。
    """
    return sorted(BOILERPLATE, key=len, reverse=True)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_vocabulary.py -q`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/parsing/ tests/unit/test_vocabulary.py
git commit -m "feat: 添加套话/连接词/高优信号三张词表"
```

---

## Task 4: 溯源引擎

**Files:**
- Create: `src/homework_compass/parsing/provenance.py`
- Create: `tests/unit/test_provenance.py`
- Reference: `poc/validate_homework.py:71-143`（移植判定逻辑，等级改名）

**Interfaces:**
- Consumes: `models.TraceLevel`、`models.TRACE_ACCEPTED`
- Produces:

```python
class TracePolicy(Enum): ZERO_TOLERANCE; ALLOW_VERB_COMPLETION
FIELD_POLICY: dict[str, TracePolicy]
def norm(s: object) -> str
def is_subseq(needle: str, hay: str) -> bool
def strip_markers(text: str) -> str          # 去掉列表序号（溯源比对前用；Task 5 的 strip_lead 是另一套 poc 兼容规则）
class Provenance:
    def __init__(self, raw_text: str) -> None
    def trace(self, value: object, *, policy: TracePolicy = TracePolicy.ZERO_TOLERANCE) -> TraceLevel
```

- [ ] **Step 1: 写失败测试——每条都对应 poc 期间踩过的真实误判**

`tests/unit/test_provenance.py`：

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_provenance.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 provenance.py**

```python
"""溯源引擎：判断「这个字段值在原文里到底有没有出处」。

分级从代价最低到最高短路判定。TOKENS_MATCH 与 PARTIAL 存在的理由都是真实误判：
生图模型和文本模型都会顺手把 P12-13 规范成 P12–P13、把「练习册」说成「完成练习册」，
一刀切的子串判定会把正确数据扔进待确认，比漏判更烦人。
放宽的边界是数字与字母词元——页码和数量永远零容错。

三条必须知道的实现约束：

1. **词元必须全部命中原文**（spec §5.2）。norm 把 "P12-13" 压成 "p1213"，
   于是 "p12"、"p1" 这类前缀也都是原文的子串；不先卡词元，截断的页码会被
   判成逐字命中。子串/子序列判定只在词元过关之后才允许生效。
2. **词元允许是原文相邻词元的拼接**。模型把 "P12-13" 写成 "P1213" 时，
   词元是 "1213" 而原文是 "12"+"13"；按「必须原样出现」判，会把正确数据
   扔进 pending——那比漏判更烦人（spec §5.3）。
3. **纯汉字值会退化**：词元集对纯汉字是空的，TOKENS_MATCH 于是退化成
   「每个字都在原文出现过」，NORMALIZED 则是「整串是原文的子序列」。
   这是词元级判定的固有代价——中文没有空格可切，只能靠字集合。
   这两级都会进 report.advisories（标黄、不阻断），家长扫一眼即可。

列表序号（"1." "2、"）不算内容：序号里的数字进了词元集，截断的页码就会
因为命中序号数字而蒙混过关，所以比对前先把序号去掉（见 strip_markers）。

已知边界（都是宁可放过、不可误剥那一侧）：

- 「抄写生字，（2）遍」这种「标点 + 括号数量」仍会被剥掉（括号前不是汉字）。
  改窄到「标点前不剥」，序号就会重新 legitimize 截断页码；两头不能两全，
  按 spec 的排序保留当前行为。代价是这种原文里的数量会被删出词元集，
  真作业可能被判成无出处。
- 「生字2)遍」这种紧跟汉字的右括号形不会被剥（它与「今天作业1)数学」的序号
  形状无法区分）。代价：这种写法的序号里的数字会留在词元集里。
"""

from __future__ import annotations

import re
from enum import Enum

from homework_compass.models import TraceLevel

# 只保留汉字、字母、数字；标点、emoji、空白、装饰符一律剥离
_KEEP = re.compile(r"[^一-鿿0-9a-zA-Z]+")
_TOK = re.compile(r"[a-z]+|\d+")
_CJK = re.compile(r"[一-鿿]")

# 列表序号：数字 + 序号分隔符 + 紧跟汉字。三种形状分开写：
# 括号形「（1）数学」的前括号必须站在非汉字边界上，否则「抄写生字（2）遍」
# 里的数量会被当成序号剥掉（剥掉就等于删掉一个真实数字，真作业反被判成杜撰）；
# 裸数字形「1.数学」允许紧跟汉字（「今天作业1.数学」也得剥，否则序号里的
# 「1」会让截断的页码「P1」蒙混过关）；
# 半角/全角右括号形「1)数学」「1）数学」没有前括号，得单开一支——但它不能吃掉
# 「(2)」这类真实数量，所以额外把前括号列进否定边界（跟在括号后的数字一律不剥）。
_ENUM_MARK = re.compile(
    r"(?<![A-Za-z0-9一-鿿-])[（(]\d{1,2}[)）]\s*(?=[\u4e00-\u9fff])"
    r"|(?<![A-Za-z0-9一-鿿\-(（(])\d{1,2}[)）]\s*(?=[\u4e00-\u9fff])"
    r"|(?<![A-Za-z0-9-])\d{1,2}[.、．]\s*(?=[\u4e00-\u9fff])"
)

# task 描述里允许补动词的最低汉字重合度。低于此值视为整条编造。
_PARTIAL_CJK_FLOOR = 0.6


class TracePolicy(Enum):
    ZERO_TOLERANCE = "zero_tolerance"
    ALLOW_VERB_COMPLETION = "allow_verb_completion"


# 哪个字段能放宽到「允许补动词」，是产品判断，不是实现细节。
FIELD_POLICY: dict[str, TracePolicy] = {
    "subject": TracePolicy.ZERO_TOLERANCE,
    "quantity": TracePolicy.ZERO_TOLERANCE,
    "requirements": TracePolicy.ZERO_TOLERANCE,
    "extras": TracePolicy.ZERO_TOLERANCE,
    "task": TracePolicy.ALLOW_VERB_COMPLETION,
}


def strip_markers(text: str) -> str:
    """去掉列表序号：「1.数学」→「数学」。

    序号不是内容。序号里的数字进了词元集，截断的页码就会蒙混过关——
    原文「1.数学练习册P12-13」里写「P1」，若「1」还在词元集里就查不出问题。

    规则要窄，宁可漏剥不可错剥：「P12-13.」句末的「13.」是页码的一部分
    （前面是连字符），「1、2页」的「1、」后面是数字（那是页码范围，不是条目序号），
    「抄写生字（2）遍」的「（2）」是数量（前面是汉字），三种都不能剥。
    剥错了就等于删掉一个真实数字，词元集随之少一个，
    「抄写生字2遍」这种真作业反而会被判成杜撰。
    已知漏网：「抄写生字，（2）遍」这种「标点 + 括号数量」仍会被剥（见模块说明）；
    「生字2)遍」这种紧跟汉字的右括号形也不剥（与序号无法区分）。
    """
    return _ENUM_MARK.sub("", text or "")


def norm(s: object) -> str:
    """去掉标点、emoji、空白与装饰符，只留汉字/字母/数字，并转小写。

    去标点是为了让「P12-13」与「P12–P13」可比；代价是分隔符信息全丢，
    所以词元必须从原文切，不能从 norm 后的串切。
    """
    return _KEEP.sub("", str(s or "")).lower()


def is_subseq(needle: str, hay: str) -> bool:
    """needle 的字符按顺序出现在 hay 中即可（允许中间插入别的字符）。

    空 needle 返回 False：空串不是「出现在 hay 里」。要判空请调用方自己判。
    """
    if not needle:
        return False
    it = iter(hay)
    return all(c in it for c in needle)


class Provenance:
    """预先算好原文的三种形态，供批量溯源判定。

    词元必须从「原文」而非 norm 后的字符串里切：norm 会把 P12-13 粘成 p1213，
    导致模型写的 P12–P13 切成 {p,12,13} 却对不上 {p,1213}。
    """

    def __init__(self, raw_text: str) -> None:
        self.raw = raw_text or ""
        # 序号先去掉：它不是内容，留着会让截断的页码蒙混过关
        clean = strip_markers(self.raw)
        self.norm = norm(clean)
        self.token_seq = _TOK.findall(clean.lower())
        self.tokens = set(self.token_seq)
        self.cjk = set(_CJK.findall(clean))

    def _has_token(self, token: str) -> bool:
        """这个词元在原文里有没有出处。

        - 原样出现 → 有；
        - 是原文相邻词元的拼接（"1213" = "12" + "13"，模型去掉了分隔符）→ 有；
        - 找不到，或只是某个原文词元的一截（"1" vs "12"）→ 没有。
        """
        if token in self.tokens:
            return True
        seq = self.token_seq
        for i in range(len(seq)):
            acc = ""
            for j in range(i, len(seq)):
                acc += seq[j]
                if acc == token:
                    return True
                if len(acc) >= len(token):
                    break
        return False

    def _sourced(self, tokens: list[str]) -> bool:
        """值的每个词元都要有出处（spec §5.2：数字与字母词元必须全部命中原文）。"""
        return all(self._has_token(t) for t in tokens)

    def trace(self, value: object, *,
              policy: TracePolicy = TracePolicy.ZERO_TOLERANCE) -> TraceLevel:
        """判定字段值在原文里的出处等级。

        空值一律 UNSOURCED：空是「没有这个字段」，不是「这个字段被杜撰」——
        要把空字段当正常处理的调用方自己判空后跳过。

        ZERO_TOLERANCE（subject/quantity/requirements/extras）差一个字就不采信；
        ALLOW_VERB_COMPLETION 只给 task 档：允许补动词（原文「练习册」→
        「完成练习册」），但前提是数字与字母词元全部命中且汉字重合度 ≥ 0.6，
        所以「P14-15」这种改页码、「观察日记一篇」这种整条编造仍会被拦住。
        """
        # 值侧也按同样的规则剥：模型逐字摘录原文时会带上「1.」，
        # 只剥源侧会把这种忠实的摘录判成无出处
        s = strip_markers(str(value or ""))
        v = norm(s)
        if not v:
            return TraceLevel.UNSOURCED
        vt = _TOK.findall(s.lower())
        vc = set(_CJK.findall(s))
        # 词元闸在前：数字/字母词元没全部命中原文，就不许走子串/子序列判定。
        # norm 把 "P12-13" 压成 "p1213"，没有这道闸，"P1"（P12-13 的截断）
        # 会被子串判定当成逐字命中，页码错了还满身正装。
        if self._sourced(vt):
            if v in self.norm:
                return TraceLevel.VERBATIM
            if is_subseq(v, self.norm):
                return TraceLevel.NORMALIZED
            if vc <= self.cjk:
                return TraceLevel.TOKENS_MATCH
        if policy is TracePolicy.ALLOW_VERB_COMPLETION and self._sourced(vt) and vc:
            if len(vc & self.cjk) / len(vc) >= _PARTIAL_CJK_FLOOR:
                return TraceLevel.PARTIAL
        return TraceLevel.UNSOURCED
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_provenance.py -q`
Expected: `17 passed`

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/parsing/provenance.py tests/unit/test_provenance.py
git commit -m "feat: 添加分级溯源引擎与字段策略表"
```

---

## Task 5: 分段与噪声判定

**Files:**
- Create: `src/homework_compass/parsing/segmentation.py`
- Create: `tests/unit/test_segmentation.py`
- Reference: `poc/validate_homework.py:73-117`（`_strip_lead` / `is_noise`）、`poc/validate_homework.py:194-224`（两个切分器）

**Interfaces:**
- Consumes: `parsing.vocabulary.BOILERPLATE / CONNECTORS / boilerplate_by_len`、`parsing.provenance.norm`

  注意：`strip_lead` 走的是 poc 的 `_ENUM_LEAD`（行首锚定、含①②③），**不复用**
  `parsing.provenance.strip_markers`（内容侧、窄规则）。两者用途不同：前者决定
  片段长什么样，后者决定溯源比对前先去掉哪些序号。
- Produces:

```python
def strip_lead(text: str) -> str
def is_noise(text: str) -> bool
def split_fragments(raw: str) -> list[str]
def split_chunks_with_context(text: str) -> list[tuple[str, str]]   # (片段, 所属整句)
def split_chunks(text: str) -> list[str]
SENT_SPLIT: re.Pattern      # 句子级分隔，Task 9 的兜底解析器必须复用它
```

噪声词表全项目唯一（spec §5.5 规则 3）：`segmentation` 只准从 `vocabulary` 取词，不得自带第二张表，否则会出现"解析器丢了、校验器却报遗漏"的矛盾。

- [ ] **Step 1: 写失败测试——每条对应 poc 期间打过的一个补丁**

`tests/unit/test_segmentation.py`：

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_segmentation.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 segmentation.py**

```python
"""把原文切成可核对的片段，并判定哪些整段都是套话。

与溯源判定分开成两个文件：poc 里两者同居一室，改切分就会碰坏判定，
反之亦然；这两件事的变化方向本来就不一样。
"""

from __future__ import annotations

import re

from homework_compass.parsing.provenance import norm
from homework_compass.parsing.vocabulary import BOILERPLATE, CONNECTORS

SENT_SPLIT = re.compile(r"[；;。\n\r！？!?]+")
_CHUNK_SPLIT = re.compile(r"[，,、\s/／|｜：:]+")
_PIECE_SPLIT = re.compile(r"[，,、\s！!。~～：:]+")
_ENUM_LEAD = re.compile(r"^\s*[（(\[]?\d{1,2}[)）\].、,，]|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]+")
_LEAD_DECOR = re.compile(r"^[^0-9a-zA-Z一-鿿]+")
_HEADER = re.compile(r"(作业|任务|内容|安排|清单|事项)(如下|如下所示|以下)")
# 日期脚手架只在标题句残余判定里用，绝不能全局当套话：「明天交」是真截止时间。
_DATE_SCAFFOLD = re.compile(r"[（(][^）)]*[）)]|\d{1,4}[月日号]|今[天日]|明[天日]|昨[天日]|的")

_BOILER_NORM = {norm(x) for x in BOILERPLATE}
_BOILER_BY_LEN = sorted(_BOILER_NORM, key=len, reverse=True)
_CONN_NORM = {norm(x) for x in CONNECTORS}
_CONN_BY_LEN = sorted((x for x in CONNECTORS if x), key=len, reverse=True)
# 套话后面只允许跟极短的语气尾巴，才算同一句客套。「收到」是套话，
# 「收到书本后签字」是真作业——放开的长度就是吞掉作业的面积。
_MODAL = "好啦呀哦呢嘛啊哈"


def _is_boilerplate_piece(pn: str) -> bool:
    if not pn:
        return True
    if pn in _BOILER_NORM or pn in _CONN_NORM:
        return True
    # 「各位家长好」这类带语气后缀的变体，不能因为多一个字就被当成作业内容
    for p in _BOILER_BY_LEN:
        if pn.startswith(p) and pn != p:
            tail = pn[len(p):]
            if tail and len(tail) <= 2 and all(ch in _MODAL for ch in tail):
                return True
    return False


def strip_lead(text: str) -> str:
    """反复剥行首装饰、序号与话语连接词，直到稳定。

    连「另外」这类虚词也要剥：否则原文「另外明天记得穿校服」成了新片段，
    而抽取结果里的「明天记得穿校服」明明已覆盖它，却会因多两个字误报遗漏。
    """
    s = text or ""
    prev = None
    while prev != s:
        prev = s
        s = _LEAD_DECOR.sub("", s).strip()
        s = _ENUM_LEAD.sub("", s).strip()
        for c in _CONN_BY_LEN:
            if s.startswith(c):
                s = s[len(c):].strip("，,、：: \t")
                break
    return s


def is_noise(text: str) -> bool:
    """整段都是客套/标题/连接词则 True。含一个实义片段就不算噪声——宁可多问不可漏报。"""
    s = strip_lead(text)
    pieces = [p for p in _PIECE_SPLIT.split(s) if norm(p)]
    if not pieces:
        return True
    if all(_is_boilerplate_piece(norm(p)) for p in pieces):
        return True
    joined = "".join(pieces)
    if _HEADER.search(joined):
        residual = _DATE_SCAFFOLD.sub("", _HEADER.sub("", joined))
        residual = "".join(p for p in _PIECE_SPLIT.split(residual)
                           if not _is_boilerplate_piece(norm(p)))
        if not norm(residual):
            return True
    return False


def split_fragments(raw: str) -> list[str]:
    """句子粒度：用于给家长展示上下文。"""
    out = []
    for piece in SENT_SPLIT.split(raw or ""):
        p = strip_lead(piece).strip("　 ").lstrip("：:")
        if p and norm(p) and not is_noise(p):
            out.append(p)
    return out


def split_chunks_with_context(text: str) -> list[tuple[str, str]]:
    """词块粒度用于检测，句子粒度用于展示。

    只用粗粒度，一个已认领的词就能掩盖整句遗漏；只用细粒度，
    家长看到「今晚十点前完成」这种孤零片段会不知道该归给哪一项。
    """
    out = []
    for frag in split_fragments(text):
        for c in _CHUNK_SPLIT.split(frag):
            c = strip_lead(c).strip("　 ：:")
            if len(norm(c)) >= 2 and not is_noise(c):
                out.append((c, frag))
    return out


def split_chunks(text: str) -> list[str]:
    return [c for c, _ in split_chunks_with_context(text)]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_segmentation.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/parsing/segmentation.py tests/unit/test_segmentation.py
git commit -m "feat: 添加句子/词块双粒度分段与套话判定"
```

---

## Task 6: 校验层——字段采信与降级

校验层分两个任务落地，因为"逐字段判出处"与"整篇查遗漏"是两个可以独立测试、独立被否决的改动面。

**Files:**
- Create: `src/homework_compass/parsing/validate.py`
- Create: `tests/unit/test_validate_items.py`
- Reference: `poc/validate_homework.py:263-363`（items 循环）、`poc/validate_homework.py:385-392`（extras）
- Modify: `src/homework_compass/models.py`（补 `VALID_TYPES`，见 Step 3）

**Interfaces:**
- Consumes: `models.*`、`parsing.provenance.Provenance / TracePolicy / FIELD_POLICY`、`parsing.vocabulary.PRIORITY_MARKERS`、`errors.ExtractionError`
- Produces:

```python
def _texts(value: object) -> list[str]
def _adopt_item(idx: int, raw_item: object, prov: Provenance,
                report: ValidationReport, demoted: list[str]) -> HomeworkItem | None
def _adopt_extras(parsed: dict, prov: Provenance, report, demoted) -> list[str]
def priority_of(blob: str) -> tuple[str, list[str]]
```

- [ ] **Step 1: 写失败测试**

`tests/unit/test_validate_items.py`（`RAW` 同 Task 4）：

```python
import pytest

from homework_compass.errors import ExtractionError
from homework_compass.models import SourceKind, TraceLevel
from homework_compass.parsing.validate import priority_of, validate

RAW = "📚今日作业：1.数学练习册P12-13，家长检查后签字；2.语文抄写本课生字2遍；3.英语听读打卡Unit3"


def parsed(items, extras=None, unresolved=None):
    return {"items": items, "extras": extras or [], "unresolved": unresolved or []}


def test_happy_path_no_pending():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13",
                                "requirements": ["家长检查后签字"]},
                               {"subject": "语文", "task": "抄写本课生字", "quantity": "2遍"},
                               {"subject": "英语", "task": "听读打卡", "quantity": "Unit3"}]))
    assert len(hw.items) == 3 and hw.pending == []


@pytest.mark.xfail(reason="pending 组装在 Task 7 落地", strict=True)
def test_fabricated_requirement_dropped_rest_kept():
    """原文没有「用铅笔」，只丢这条要求，其余照常上图。"""
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13",
                                "requirements": ["用铅笔", "家长检查后签字"]}]))
    assert hw.items[0].requirements == ["家长检查后签字"]
    assert any(p.text == "用铅笔" for p in hw.pending)


@pytest.mark.xfail(reason="pending 组装在 Task 7 落地", strict=True)
def test_fabricated_subject_blanked_not_shown():
    hw = validate(RAW, parsed([{"subject": "音乐", "task": "练习册", "quantity": "P12-13"}]))
    assert hw.items[0].subject == ""
    assert any("音乐" in p.text for p in hw.pending)


def test_whole_task_fabricated_drops_item():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "观察天象", "quantity": ""}]))
    assert hw.items == []


def test_empty_task_dropped_with_note():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "", "quantity": ""}]))
    assert hw.items == [] and hw.report.notes


def test_seq_renumbered_after_drops():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"},
                               {"subject": "体育", "task": "观察天象", "quantity": ""},
                               {"subject": "语文", "task": "抄写本课生字", "quantity": "2遍"}]))
    assert [i.seq for i in hw.items] == [1, 2]


def test_priority_program_overrides_llm():
    hw = validate(RAW, parsed([{"subject": "语文", "task": "抄写本课生字",
                                "quantity": "2遍", "priority": "high"}]))
    assert hw.items[0].priority == "normal"
    assert hw.report.priority_overrides


def test_priority_marker_survives_requirement_dedup():
    """整句当 task、又重复列要求时，去重不能把「签字」信号一起去掉。"""
    text = "1.数学：完成练习册，家长签字"
    hw = validate(text, parsed([{"subject": "数学", "task": "完成练习册，家长签字",
                                 "quantity": "", "requirements": ["家长签字"]}]))
    assert hw.items[0].requirements == []
    assert hw.items[0].requirements_all == ["家长签字"]
    assert hw.items[0].priority == "high"


def test_invalid_type_becomes_unknown():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册",
                                "quantity": "P12-13", "type": "考试"}]))
    assert hw.items[0].type == "unknown"


def test_fabricated_extra_becomes_pending():
    hw = validate(RAW, parsed([], extras=["带跳绳"]))
    assert hw.extras == []


@pytest.mark.parametrize("bad", ["not-a-dict", {"no_items": 1}, {"items": "x"}])
def test_structural_failure_raises_not_silently(bad):
    with pytest.raises(ExtractionError):
        validate(RAW, bad if isinstance(bad, dict) else {})


def test_provenance_recorded_per_field():
    hw = validate(RAW, parsed([{"subject": "数学", "task": "完成练习册",
                                "quantity": "P12-13"}]))
    assert hw.items[0].provenance["quantity"] is TraceLevel.VERBATIM
    assert hw.items[0].provenance["task"] is TraceLevel.PARTIAL


def test_pending_flagged_in_advisories_not_blocked():
    """规范化过但采信的字段绝不进 pending，否则补动词就出不了图。

    破折号写法（P12-13 → P12–13）不算规范化：norm 剥掉全部标点后两者相同，
    判 VERBATIM，连 advisory 都不进。真正会进 advisory 的是 task 补动词。
    """
    text = "1.数学练习册P12-13"
    hw = validate(text, parsed([{"subject": "数学", "task": "完成练习册",
                                 "quantity": "P12–13"}]))
    assert hw.pending == []
    assert hw.items[0].task == "完成练习册"
    assert any(r.level is TraceLevel.PARTIAL for r in hw.report.advisories)


def test_fabricated_page_number_is_not_adopted():
    """页码零容错（spec §5.2）：原文只有 P12-13 时，P14-15 不得上图。

    不采信这个页码——置空并留痕，绝不把错页码印到孩子桌上。
    """
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P14-15"}]))
    assert hw.items[0].quantity == ""
    assert hw.items[0].provenance["quantity"] is TraceLevel.UNSOURCED
    assert any("quantity" in n or "页码" in n for n in hw.report.notes)


def test_priority_of_returns_signals():
    priority, signals = priority_of("数学 家长签字")
    assert priority == "high" and "签字" in signals
    assert priority_of("数学 练习册") == ("normal", [])


def test_requirements_given_as_string_not_exploded():
    """模型把单个要求写成裸字符串时，不能逐字符展开成一条条要求。"""
    hw = validate(RAW, parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13",
                                "requirements": "家长检查后签字"}]))
    assert hw.items[0].requirements == ["家长检查后签字"]


def test_extras_given_as_string_treated_as_one_item():
    text = "1.数学练习册P12-13；带跳绳"
    hw = validate(text, parsed([{"subject": "数学", "task": "练习册",
                                 "quantity": "P12-13"}], extras="带跳绳"))
    assert hw.extras == ["带跳绳"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_validate_items.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 validate.py（本任务只到 items/extras，覆盖率检查在 Task 7）**

先在 `models.py` 追加一行枚举白名单（上游 schema 的 `type` 取值）：

```python
VALID_TYPES: frozenset[str] = frozenset({"written", "oral", "reading", "checkin", "material"})
```

`src/homework_compass/parsing/validate.py`：

```python
"""机械校验层（承重墙）。三条不变量，改任何一行前必须先证明没破坏它们：

1. 溯源：字段值必须在原文有出处，否则不采信。
2. 覆盖：原文每个实义片段必须被认领，否则回问家长。
3. 闸门：pending 非空 → 上层拒绝出图。

分级严宽的依据是代价：硬事实（科目/页码/数量/要求）错一个字就是错，零容错；
task 描述允许模型补动词（原文「练习册」→「完成练习册」），否则几乎每项都被拦，
产品就没法用了。放宽的边界永远是数字与字母词元——页码不许被补出来。
"""

from __future__ import annotations

from homework_compass.errors import ExtractionError
from homework_compass.models import (
    ADVISORY_LEVELS, VALID_TYPES, HomeworkItem, ParsedHomework, SourceKind,
    TraceLevel, TraceRecord, ValidationReport,
)
from homework_compass.parsing.provenance import FIELD_POLICY, Provenance, norm
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
```

- [ ] **Step 4: 临时补一个最小 `validate()` 让测试可跑**

本任务先实现到"能出 items/extras"，`validate()` 末尾暂以 `pending=[]` 返回，Task 7 再把覆盖率与 pending 补齐：

```python
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
    return hw
```

Run: `python3 -m pytest tests/unit/test_validate_items.py -q`
Expected: `17 passed, 2 xfailed`。两个 xfail（`test_fabricated_requirement_dropped_rest_kept`、`test_fabricated_subject_blanked_not_shown`）断言 pending 内容，标 `strict=True` 等 Task 7 组装 pending；Task 7 结束时**必须删掉这两个 xfail**。

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/parsing/validate.py src/homework_compass/models.py tests/unit/test_validate_items.py
git commit -m "feat: 校验层字段采信与降级（硬事实零容错、task 允许补动词）"
```

---

## Task 7: 校验层——覆盖率检查与 pending 组装

**Files:**
- Modify: `src/homework_compass/parsing/validate.py`（补 `claimed_text` / 覆盖检查 / pending 组装）
- Create: `tests/unit/test_validate_coverage.py`
- Reference: `poc/validate_homework.py:231-255`（`claimed_text`）、`poc/validate_homework.py:365-428`（覆盖 + 套话过滤）

**Interfaces:**
- Consumes: `Task 5 split_chunks_with_context`、`Task 6 validate()`、`models.PendingItem / PendingReason`
- Produces:

```python
def claimed_text(hw: ParsedHomework, *, include_pending: bool = False) -> str
def coverage_gaps(raw_text: str, hw: ParsedHomework) -> list[tuple[str, str]]
def build_pending(hw: ParsedHomework, demoted: list[str], model_unresolved: list[str],
                  gaps: list[tuple[str, str]],
                  source_kind: SourceKind = SourceKind.TEXT) -> list[PendingItem]
```

Task 6 的 `validate.py` 顶部 import 需要补上 `PendingReason`（本任务开始用到它）。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_validate_coverage.py`：

```python
from homework_compass.models import PendingReason, SourceKind
from homework_compass.parsing.validate import claimed_text, validate

RAW2 = ("各位家长好！今天（11月5日）的作业如下：\n"
        "①语文：《静夜思》背诵并默写，家长签字\n②数学：练习册第12-13页\n"
        "⑤美术：准备好彩泥和剪刀\n另外明天记得穿校服。\n收到请回复，谢谢！")


def parsed(items, extras=None, unresolved=None):
    return {"items": items, "extras": extras or [], "unresolved": unresolved or []}


def test_subject_counts_toward_claimed_text():
    """原文写「英语听读打卡」，拆成 subject+task 后不拼回去就会误报遗漏。"""
    hw = validate("1.英语听读打卡Unit3",
                  parsed([{"subject": "英语", "task": "听读打卡", "quantity": "Unit3"}]))
    assert hw.pending == []


def test_dropped_line_becomes_uncovered_pending():
    hw = validate(RAW2 + "\n⑥科学：观察植物的变化",
                  parsed([{"subject": "语文", "task": "《静夜思》背诵并默写",
                           "requirements": ["家长签字"]},
                          {"subject": "数学", "task": "练习册", "quantity": "第12-13页"},
                          {"subject": "美术", "task": "准备好彩泥和剪刀"},
                          {"subject": "科学", "task": "观察植物的变化"}],
                          extras=["明天记得穿校服"]))
    texts = "；".join(claimed_text(hw).split())
    assert "收到请回复" not in texts            # 套话不进气泡
    reasons = {p.reason for p in hw.pending}
    assert PendingReason.UNCOVERED in reasons or hw.pending == []


def test_boilerplate_from_model_never_reaches_parent():
    """poc 缺陷：模型把客套话堆进 unresolved，透传后家长每天确认一堆废话。"""
    hw = validate("1.数学练习册P12-13",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                         unresolved=["各位家长好", "今天作业如下", "收到请回复"]))
    assert hw.pending == []


def test_real_omission_still_reported_after_boilerplate_filter():
    hw = validate("1.数学练习册P12-13；明天带美术材料：彩泥",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                         unresolved=["各位家长好"]))
    assert [p.text for p in hw.pending] == ["明天带美术材料：彩泥"] or any(
        "美术材料" in p.text for p in hw.pending)
    assert all(p.reason is not None for p in hw.pending)


def test_pending_has_context_and_related_seq():
    hw = validate("1.数学：完成练习册P12-13\n2.明天带美术材料：彩泥",
                  parsed([{"subject": "数学", "task": "完成练习册", "quantity": "P12-13"}]))
    assert hw.pending
    p = hw.pending[0]
    assert p.source_sentence            # 家长看得见它出自哪一句
    assert p.id                         # 销账靠 id，不靠文案


def test_pending_ids_unique():
    hw = validate("1.数学练习册P12-13\n2.语文练习册P14-15\n3.英语单词表",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"},
                          {"subject": "语文", "task": "练习册", "quantity": "P14-15"}]))
    assert len({p.id for p in hw.pending}) == len(hw.pending)


def test_ocr_source_always_blocks():
    hw = validate("1.数学练习册P12-13",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}]),
                  source_kind=SourceKind.OCR)
    assert [p.reason for p in hw.pending] == [PendingReason.OCR_UNVERIFIED]


def test_claimed_text_excludes_pending_by_default():
    """否则待确认项自己认领自己，永远销不掉——poc 的死胡同。"""
    hw = validate("1.数学练习册P12-13\n2.明天带美术材料",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}]))
    assert hw.pending
    assert "美术材料" not in claimed_text(hw)
    assert "美术材料" in claimed_text(hw, include_pending=True)


def test_same_text_from_two_sources_yields_one_pending():
    """模型自认含糊的那段同时又是覆盖率缺口时，不能变成两条一样的待确认。"""
    hw = validate("1.数学练习册P12-13\n2.明天带美术材料",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                         unresolved=["明天带美术材料"]))
    assert [p.text for p in hw.pending] == ["明天带美术材料"]


def test_report_uncovered_matches_stats_and_excludes_boilerplate():
    """审计面只列真正的覆盖率缺口；套话在分段层就被挡掉，不冒充遗漏。"""
    hw = validate("1.数学练习册P12-13\n2.明天带美术材料\n收到请回复",
                  parsed([{"subject": "数学", "task": "练习册", "quantity": "P12-13"}]))
    assert hw.report.uncovered == ["明天带美术材料"]
    assert hw.report.stats["uncovered"] == len(hw.report.uncovered)
    assert all("收到" not in u for u in hw.report.uncovered)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_validate_coverage.py -q`
Expected: `ImportError: cannot import name 'claimed_text'`

- [ ] **Step 3: 补全 validate.py**

追加三个函数，并把 `validate()` 结尾从"pending 为空"改成真正的组装：

```python
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
    from homework_compass.parsing.segmentation import is_noise
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
```

`validate()` 末尾（构造 `hw` 之后、`return hw` 之前）替换为：

```python
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
```

注意：`coverage_gaps` 必须在 `hw` 构造之后调用，它依赖已采信项的 `claimed_text`；`demoted` 里的内容已不在 items 中，不会自我覆盖。

- [ ] **Step 4: 跑全部校验测试确认通过**

Run: `python3 -m pytest tests/unit -q`
Expected: `75 passed`（其中 `test_validate_coverage.py` 10 passed），且 Task 6 加的 xfail 已删除（`grep -rn "xfail" tests/` 应无输出）。

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/parsing/validate.py tests/unit/test_validate_coverage.py tests/unit/test_validate_items.py
git commit -m "feat: 校验层覆盖率检查与四路 pending 组装"
```

---

## Task 8: 销账——correct / dismiss

**Files:**
- Modify: `src/homework_compass/parsing/validate.py`（追加 `correct` / `dismiss` / `is_covered`）
- Create: `tests/unit/test_confirmation.py`

**Interfaces:**
- Consumes: `Task 7 claimed_text / coverage 判定`、`models.PendingItem.id`
- Produces:

```python
EDITABLE_FIELDS: frozenset[str]
def is_covered(text: str, hw: ParsedHomework) -> bool
def correct(hw: ParsedHomework, seq: int, field: str, value: str) -> ParsedHomework
def dismiss(hw: ParsedHomework, pending_id: str) -> ParsedHomework
```

三个不可回退的细节（spec §5.7）：销账口径与提出口径一致；销账靠 `pending_id` 而非文案子串；算"已认领文本"时必须排除 pending 自身。

- [ ] **Step 1: 写失败测试——这四条就是 poc 死胡同的护栏**

```python
import pytest

from homework_compass.models import PendingReason, SourceKind, TraceLevel
from homework_compass.parsing.validate import correct, dismiss, is_covered, validate

RAW = "1.数学：完成练习册P12-13\n2.明天带美术材料：彩泥"


def hw_with_pending():
    return validate(RAW, {"items": [{"subject": "数学", "task": "完成练习册",
                                     "quantity": "P12-13"}],
                          "extras": [], "unresolved": []})


def test_confirmation_loop_is_not_a_dead_end():
    """poc 初版：--set 改完字段，unresolved 永远清不掉，图永远生不成。"""
    hw = hw_with_pending()
    assert hw.pending
    after = correct(hw, seq=1, field="requirements", value="明天带美术材料：彩泥")
    assert after.pending == []


def test_correct_on_wrong_target_keeps_pending():
    hw = hw_with_pending()
    after = correct(hw, seq=1, field="quantity", value="P12-14")
    assert after.pending == hw.pending      # 没承接上就留着，宁可多问一次


def test_original_object_not_mutated():
    hw = hw_with_pending()
    before = [p.id for p in hw.pending]
    correct(hw, seq=1, field="requirements", value="明天带美术材料：彩泥")
    assert [p.id for p in hw.pending] == before


def test_dismiss_only_touches_named_pending():
    hw = validate("1.数学练习册P12-13\n2.明天带美术材料\n3.后天交科学记录单",
                  {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                   "extras": [], "unresolved": []})
    assert len(hw.pending) >= 2
    target = hw.pending[0]
    after = dismiss(hw, target.id)
    assert target.id not in [p.id for p in after.pending]
    assert [p.text for p in after.pending] == [p.text for p in hw.pending[1:]]


def test_ocr_pending_can_be_dismissed():
    hw = validate("1.数学练习册P12-13",
                  {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                   "extras": [], "unresolved": []}, source_kind=SourceKind.OCR)
    pid = next(p.id for p in hw.pending if p.reason is PendingReason.OCR_UNVERIFIED)
    assert dismiss(hw, pid).pending == []


@pytest.mark.parametrize("field", ["seq", "provenance", "requirements_all", "nope"])
def test_non_whitelist_field_rejected(field):
    from homework_compass.parsing.validate import EDITABLE_FIELDS
    hw = hw_with_pending()
    with pytest.raises(ValueError, match="白名单"):
        correct(hw, seq=1, field=field, value="x")
    assert "task" in EDITABLE_FIELDS and "d1" not in EDITABLE_FIELDS


def test_is_covered_excludes_pending_itself():
    hw = hw_with_pending()
    p = hw.pending[0]
    assert not is_covered(p.text, hw)


def test_manual_correction_is_recorded_in_notes():
    hw = hw_with_pending()
    after = correct(hw, seq=1, field="requirements", value="明天带美术材料：彩泥")
    assert any("家长修正" in n for n in after.report.notes)


def test_corrected_field_is_not_claimed_verbatim():
    """家长改出来的值不在原文里，审计数据不能还写着 verbatim。"""
    hw = hw_with_pending()
    after = correct(hw, seq=1, field="quantity", value="P12-14")
    assert after.items[0].quantity == "P12-14"
    assert after.items[0].provenance["quantity"] is TraceLevel.NORMALIZED


def test_correct_recomputes_priority():
    hw = hw_with_pending()
    after = correct(hw, seq=1, field="requirements", value="家长签字")
    assert after.items[0].priority == "high"
    assert "签字" in after.items[0].priority_signals


def test_correct_rejects_type_outside_enum():
    """可改不等于乱改：type 仍只能取枚举内的值。"""
    hw = hw_with_pending()
    with pytest.raises(ValueError, match="type"):
        correct(hw, seq=1, field="type", value="考试")
    assert correct(hw, seq=1, field="type", value="reading").items[0].type == "reading"


def test_correct_refreshes_uncovered_report():
    """改对了就不该再在审计面上显示「原文有、数据没有」。"""
    hw = hw_with_pending()
    # 冒号也分词块，所以一句「明天带美术材料：彩泥」是两条待确认（
    # poc 同口径：一个已认领的词不能掩盖剩下的遗漏）。
    assert hw.report.uncovered == ["明天带美术材料", "彩泥"]
    after = correct(hw, seq=1, field="requirements", value="明天带美术材料：彩泥")
    assert after.report.uncovered == []
    assert after.report.stats["uncovered"] == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_confirmation.py -q`
Expected: `ImportError: cannot import name 'correct'`

- [ ] **Step 3: 实现**

```python
EDITABLE_FIELDS: frozenset[str] = frozenset(
    {"subject", "task", "quantity", "requirements", "priority", "type"})


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
```

`validate.py` 顶部需补 `import re` 与 `from dataclasses import replace`。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit -q`
Expected: `90 passed`（其中 `test_confirmation.py` 15 passed）。

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/parsing/validate.py tests/unit/test_confirmation.py
git commit -m "feat: 家长确认销账 correct/dismiss（口径与提出口径一致）"
```

---

## Task 9: 抽取协议与两个离线 extractor

**Files:**
- Create: `src/homework_compass/parsing/extract.py`
- Create: `tests/unit/test_extract_offline.py`
- Reference: `poc/parse_homework.py:44-87`（`clean_line` / `find_subject` / `naive_extract`）

**Interfaces:**
- Consumes: `parsing.segmentation.SENT_SPLIT / strip_lead / is_noise`、`parsing.vocabulary.BOILERPLATE`
- Produces:

```python
class Extractor(Protocol):
    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict: ...
class NaiveExtractor:                 # 离线兜底
class StubExtractor:                  # 测试注入
    def __init__(self, payload: dict | list[dict]) -> None
SUBJECTS: list[str]
```

**本版对 poc 的一处刻意改进（会体现在 Task 18 平价差异里）**：poc 的兜底解析器对 raw2 得到 **7 项**，第 1 项是 `好！今天（11月5日）的作业如下：` 这串垃圾。原因有两层：按行（`\n；;`）切条只是让整串客套话留在同一片里，真正让它活下来的是 `_LABEL` 的零个或多个量词——`各位家长好` 被剥掉 `各位家长` 后只剩 `好`，`is_noise` 认不出它，于是**当成正文第一项印上了 A4 纸**。只换成 `SENT_SPLIT` 并不够（实测：切出 `各位家长好` 后照样剩一个 `好`）。本版两处一起改：① 改用 `segmentation.SENT_SPLIT`（含 `！？。`）切句，让整句客套话完整落到 `is_noise` 手里；② `_LABEL` 的量词改成 `+`，标签后面必须跟分隔符才算标签。raw2 离线路径因此降到 6 项，`test_greeting_leaves_no_residue_after_label_strip` / `test_raw2_offline_yields_six_real_items` 锁住这个行为。理由：兜底解析器可以笨，但不能把客套话印到孩子桌上。

- [ ] **Step 1: 写失败测试**

```python
from homework_compass.parsing.extract import NaiveExtractor, StubExtractor, naive_extract

NAIVE = NaiveExtractor()


def naive(raw: str) -> list[dict]:
    return naive_extract(raw)["items"]


def test_clean_line_strips_decor_enum_label():
    got = naive("📚今日作业：\n1.③英语：听读打卡Unit3")
    assert [i["task"] for i in got] == ["英语：听读打卡Unit3"] or \
           [i["task"] for i in got] == ["听读打卡Unit3"]


def test_page_number_starting_with_letter_survives():
    """序号正则很凶，P12-13 不能被当成「P. 」之类误剥。"""
    assert any("P12-13" in i["task"] + i["quantity"] for i in naive("1.P12-13 练习册"))


def test_subject_recognised_midline():
    assert naive("1.完成数学练习册P12-13")[0]["subject"] == "数学"


def test_subject_not_split_out_of_material_phrase():
    """「美术材料」≠ 美术课。误拆会把关键字从任务里挖走。"""
    it = naive("1.明天带美术材料：彩泥")[0]
    assert it["subject"] == ""
    assert "美术材料" in it["task"]


def test_boilerplate_lines_never_become_items():
    raw = ("各位家长好！今天（11月5日）的作业如下：\n①语文：背诵《静夜思》\n"
           "另外明天记得穿校服。\n收到请回复，谢谢！")
    tasks = " ".join(i["task"] for i in naive(raw))
    assert "各位家长" not in tasks
    assert "作业如下" not in tasks                      # ← 本版修掉的 poc 缺陷
    assert "收到请回复" not in tasks


def test_empty_input_yields_no_items():
    assert naive_extract("")["items"] == []


def test_greeting_leaves_no_residue_after_label_strip():
    """「各位家长好」不能因为剥掉「各位家长」只剩一个「好」就变成作业项。"""
    tasks = [i["task"] for i in naive("各位家长好！今天（11月5日）的作业如下：\n①语文：背诵《静夜思》")]
    assert tasks == ["背诵《静夜思》"]


def test_raw2_offline_yields_six_real_items():
    """raw2 离线路径：客套/标题句不占位，六项实义内容不增不减。"""
    raw = ("各位家长好！今天（11月5日）的作业如下：\n"
           "①语文：《静夜思》背诵并默写，家长签字\n"
           "②数学：练习册第12-13页，完成后校对答案\n"
           "③英语：跟读Unit3 A部分单词，APP打卡\n"
           "④科学：观察植物的变化，写一篇观察日记（下周三交）\n"
           "⑤美术：准备好彩泥和剪刀\n"
           "另外明天记得穿校服，书包里放好水彩笔。\n"
           "收到请回复，谢谢！")
    tasks = [i["task"] for i in naive(raw)]
    assert len(tasks) == 6
    assert [i["subject"] for i in naive(raw)] == ["语文", "数学", "英语", "科学", "美术", ""]
    assert not any("各位家长" in t or "作业如下" in t or "收到请回复" in t for t in tasks)


def test_naive_then_validate_is_clean():
    from homework_compass.parsing.validate import validate
    raw = "1.数学：练习册P12-13，家长签字\n2.语文：抄写生字2遍"
    hw = validate(raw, NAIVE(raw))
    assert len(hw.items) == 2 and hw.pending == []


def test_priority_survives_naive_path():
    from homework_compass.parsing.validate import validate
    hw = validate("1.数学：家长签字确认", NAIVE("1.数学：家长签字确认"))
    assert hw.items[0].priority == "high"


def test_stub_extractor_can_queue():
    stub = StubExtractor([{"items": []}, {"items": [{"task": "x"}]}])
    assert stub("任意") == {"items": []}
    assert stub("任意") == {"items": [{"task": "x"}]}
    assert stub("任意") == {"items": [{"task": "x"}]}   # 最后一个重复用
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_extract_offline.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 extract.py（离线部分）**

```python
"""抽取层：只负责给出候选，不负责给出真相。可信度由 validate 的机械校验决定。

三个实现走同一协议，校验层不知道上游是谁——poc 里的 `--no-llm` if 分支
到此变成正式设计：降级路径与主路径共用同一套校验。
"""

from __future__ import annotations

import re
from typing import Protocol

from homework_compass.parsing.segmentation import SENT_SPLIT, is_noise, strip_lead
from homework_compass.parsing.vocabulary import BOILERPLATE

SUBJECTS = ["语文", "数学", "英语", "科学", "美术", "音乐", "体育",
            "道德与法治", "道法", "劳动", "阅读", "写字"]
# 科目后面紧跟这些字时它是定语不是科目（「美术材料」≠ 美术课）。
_SUBJECT_BLOCK = ("材料", "用具", "工具", "课本", "书", "老师")
# 标签后面必须跟分隔符才算标签。「各位家长好」里的「各位家长」不是标签——
# 把它剥掉只剩「好」，套话判定就认不出来，客套句照样会印上纸。
_LABEL = re.compile("^(" + "|".join(re.escape(w)
                   for w in sorted(BOILERPLATE, key=len, reverse=True)) + r")[：:，,\s]+")


class Extractor(Protocol):
    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict: ...


def clean_line(line: str) -> str:
    prev = None
    s = (line or "").strip()
    while prev != s:
        prev = s
        s = strip_lead(s)
        s = _LABEL.sub("", s).strip()
        s = s.lstrip("：:，,、 ")
    return s


def find_subject(line: str) -> tuple[int, str]:
    hits = []
    for s in SUBJECTS:
        start = line.find(s)
        while start != -1:
            if not line[start + len(s):].startswith(_SUBJECT_BLOCK):
                hits.append((start, s))
                break
            start = line.find(s, start + 1)
    return min(hits) if hits else (-1, "")


def naive_extract(raw: str) -> dict:
    """离线兜底：按句拆条、行内最早出现的科目词归为科目。刻意做笨。"""
    items = []
    for piece in SENT_SPLIT.split(raw or ""):
        line = clean_line(piece)
        if not line or is_noise(line):
            continue
        pos, subject = find_subject(line)
        task = line if pos < 0 else (line[:pos] + line[pos + len(subject):]).strip("：:，,、 ")
        if not task:
            task, subject = line, ""
        items.append({"subject": subject, "task": task, "quantity": "", "requirements": []})
    return {"items": items, "extras": [], "unresolved": []}


class NaiveExtractor:
    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict:
        return naive_extract(raw_text)


class StubExtractor:
    """测试注入。给一个 dict 就一直返回它，给列表则依次返回、最后一个重复用。"""

    def __init__(self, payload: dict | list[dict]) -> None:
        self._queue = [payload] if isinstance(payload, dict) else list(payload)
        if not self._queue:
            raise ValueError("StubExtractor 至少需要一个 payload")

    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict:
        return self._queue[0] if len(self._queue) == 1 else self._queue.pop(0)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_extract_offline.py -q`
Expected: `11 passed`（全量 `101 passed`）

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/parsing/extract.py tests/unit/test_extract_offline.py
git commit -m "feat: Extractor 协议 + 离线兜底与测试桩（客套句不再成为作业项）"
```

---

## Task 10: LLM 客户端与在线 extractor

**Files:**
- Create: `src/homework_compass/llm_client.py`
- Modify: `src/homework_compass/parsing/extract.py`（追加 `LlmExtractor` / `ocr_to_text`）
- Create: `tests/unit/test_llm_client.py`
- Create: `tests/network/test_real_extract.py`
- Reference: `poc/dashscope_common.py`（全文 86 行）、`poc/llm_extract.py:20-39`（提示词）、`poc/llm_extract.py:46-111`

**Interfaces:**
- Consumes: `errors.ApiError / ExtractionError`、`config.load_dotenv_default`（Task 14 提供，本任务先用 `os.environ` 直读）
- Produces:

```python
KEY_ENV: str                            # "DASHSCOPE_API_KEY"
def api_key() -> str
def post(url: str, payload: dict, *, timeout: int = 120) -> dict
def compatible_url(path: str) -> str
def chat(content: list[dict], model: str, *, system: str, response_format: dict | None = None,
         timeout: int = 120, transport=None) -> str
def ocr_to_text(image_path: Path, *, model: str = "qwen-vl-ocr", timeout: int = 120,
                transport=None) -> str

class LlmExtractor:
    def __init__(self, *, model: str = "qwen-plus", transport=None) -> None
    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict
```

- [ ] **Step 1: 写失败测试（单元层零网络：注入假 transport）**

`tests/unit/test_llm_client.py`：

```python
import pytest

from homework_compass.errors import ApiError, ExtractionError
from homework_compass.parsing.extract import SYSTEM_PROMPT, LlmExtractor


class FakePost:
    def __init__(self, body):
        self.body, self.calls = body, []

    def __call__(self, url, payload, *, timeout=120):
        self.calls.append((url, payload))
        return self.body


def ok(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_prompt_constraints_are_present_in_payload():
    fake = FakePost(ok('{"items": []}'))
    LlmExtractor(transport=fake)("1.数学练习册", date="2026-11-06", name="小宇")
    _, payload = fake.calls[0]
    assert payload["temperature"] == 0
    assert payload["response_format"] == {"type": "json_object"}   # 缺了接口会报错
    assert "逐字摘录" in payload["messages"][0]["content"]
    assert "不要输出 priority" in SYSTEM_PROMPT


@pytest.mark.parametrize("fence", ["```json", "```JSON", "```"])
def test_fences_are_stripped_before_json(fence):
    fake = FakePost(ok(f"{fence}\n{{\"items\": []}}\n```"))
    assert LlmExtractor(transport=fake)("x") == {"items": []}


def test_illegal_json_is_extraction_error_not_silent_none():
    fake = FakePost(ok("我觉得应该这样写……"))
    with pytest.raises(ExtractionError, match="JSON"):
        LlmExtractor(transport=fake)("x")


def test_top_level_list_is_rejected():
    fake = FakePost(ok("[1,2]"))
    with pytest.raises(ExtractionError, match="不是对象"):
        LlmExtractor(transport=fake)("x")


def test_empty_source_text_never_costs_money():
    fake = FakePost(ok("{}"))
    with pytest.raises(ExtractionError, match="为空"):
        LlmExtractor(transport=fake)("   ")
    assert fake.calls == []


def test_error_body_raises_api_error_with_actionable_text():
    fake = FakePost({"error": {"message": "model not activated"}})
    with pytest.raises(ApiError, match="model not activated"):
        LlmExtractor(transport=fake)("x")


@pytest.mark.parametrize("code,keyword", [(401, "API Key"), (404, "端点")])
def test_http_errors_are_translated(monkeypatch, code, keyword):
    import urllib.error

    from homework_compass import llm_client as lc

    def boom(req, **kw):
        raise urllib.error.HTTPError(req.full_url, code, "no", {}, None)

    monkeypatch.setattr(lc.urllib.request, "urlopen", boom)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    with pytest.raises(ApiError, match=keyword):
        lc.post("https://example.invalid", {})


def test_missing_key_message_names_the_env_var(monkeypatch):
    from homework_compass import llm_client as lc
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(ApiError, match="DASHSCOPE_API_KEY"):
        lc.api_key()


def test_ocr_returns_stripped_text_and_sends_inline_image(tmp_path):
    from homework_compass.parsing.extract import ocr_to_text
    img = tmp_path / "board.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    fake = FakePost(ok("  1.数学：P12  \n"))
    assert ocr_to_text(img, transport=fake) == "1.数学：P12"
    _, payload = fake.calls[0]
    user = payload["messages"][1]["content"]
    assert user[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert payload["messages"][0]["content"].startswith("你是 OCR 转写器")
    assert payload["temperature"] == 0


def test_ocr_missing_file_never_costs_money(tmp_path):
    from homework_compass.parsing.extract import ocr_to_text
    fake = FakePost(ok("x"))
    with pytest.raises(ExtractionError, match="图片不存在"):
        ocr_to_text(tmp_path / "nope.png", transport=fake)
    assert fake.calls == []
```

- [ ] **Step 2: 实现 llm_client.py**

移植 `poc/dashscope_common.py`，三处必须改动：

1. 异常改用 `errors.ApiError`（删掉本地 `class ApiError`），不要出现第二个异常层级。
2. `get_api_key` → `api_key`，只读 `os.environ`；错误文案里的路径改成 `config.toml` 之外的说明（不得提示"写进配置文件"）。
3. `post` 增加 `retry_after_seconds` 处理：429 与 5xx 各重试一次、间隔 2s，其它码直接抛。

```python
"""百炼 DashScope 传输层：鉴权、POST、错误翻译。

已知坑（实测踩过，写在这里省掉下一个人的半小时）：
- `response_format={"type":"json_object"}` 要求提示词里出现 "JSON" 字样，否则 400。
- 业务空间（workspace）维度的 key 形如 `sk-ws-...`，老域名可能不认，需要专属域名。
- 生图返回的 URL 24 小时失效。本版不生图，但接生图的那个 spec 必须立刻下载落盘。
- key 只从环境变量读：凭证一旦进 config.toml，就会被顺手提交。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from homework_compass.errors import ApiError, ExtractionError

KEY_ENV = "DASHSCOPE_API_KEY"
COMPATIBLE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
NATIVE_BASE = "https://dashscope.aliyuncs.com"
_RETRYABLE = (429, 500, 502, 503)


def api_key() -> str:
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise ApiError(
            f"未设置环境变量 {KEY_ENV}。请 `export {KEY_ENV}=sk-xxx`"
            "（百炼控制台生成，通常 30+ 位）。凭证不要写进 config.toml。"
        )
    return key


def compatible_url(path: str) -> str:
    root = (os.environ.get("DASHSCOPE_BASE_URL") or COMPATIBLE_BASE).rstrip("/")
    return f"{root}/{path.lstrip('/')}"


def post(url: str, payload: dict, *, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key()}"}
    for attempt in range(2):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            if e.code in _RETRYABLE:
                if attempt == 0:
                    time.sleep(2)
                    continue
                raise ApiError(
                    f"HTTP {e.code}（已自动重试一次仍失败）：{detail or '<空响应体>'}\n"
                    "限流或服务端抖动通常过一会儿就好；连续出现请稍后再试。"
                ) from e
            if e.code in (401, 403):
                raise ApiError(
                    f"HTTP {e.code} API Key 无效或被拒：{detail or '<空响应体>'}\n"
                    f"请确认 {KEY_ENV} 是完整 key（sk- 开头）、已开通该模型权限；"
                    "若 key 曾在对话/日志里明文出现过，请先在控制台轮换。"
                ) from e
            if e.code == 404:
                raise ApiError(
                    f"HTTP 404（端点或模型不可用）：{url} —— {detail or '<空响应体>'}\n"
                    "可能原因：模型不在此接入方式下、地域不对（国际站用 "
                    "dashscope-intl.aliyuncs.com）、或业务空间 Key 需改用专属域名。"
                ) from e
            if e.code == 400 and "json" in detail.lower():
                raise ApiError(
                    f"HTTP 400：{detail}\n提示：结构化输出要求提示词中出现 “JSON” 字样。"
                ) from e
            raise ApiError(f"HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise ApiError(f"网络错误：{e.reason}。请重试，或调大 timeout（当前 {timeout}s）。") from e
        except TimeoutError as e:
            raise ApiError(f"请求超时（{timeout}s）：请重试或调大 timeout。") from e
    raise ApiError("重试后仍失败：未收到可用的响应。")


def check_body_error(body: dict) -> None:
    """两种协议错误字段不同：兼容模式是 error{}，原生是顶层 code/message。"""
    if body.get("error"):
        raise ApiError(f"接口返回错误：{json.dumps(body['error'], ensure_ascii=False)}")
    if body.get("code"):
        raise ApiError(f"接口错误 {body['code']}: {body.get('message', '')}")


def chat(content: list[dict], model: str, *, system: str,
         response_format: dict | None = None, timeout: int = 120,
         transport=None) -> str:
    payload: dict = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": content}],
        "temperature": 0,      # 抄写型任务不需要创造性
    }
    if response_format:
        payload["response_format"] = response_format
    body = (transport or post)(compatible_url("chat/completions"), payload, timeout=timeout)
    check_body_error(body)
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ExtractionError(
            f"响应结构异常：{json.dumps(body, ensure_ascii=False)[:500]}") from e
```

- [ ] **Step 3: 给 extract.py 追加在线 extractor**

移植 `poc/llm_extract.py` 的 `SYSTEM_PROMPT`（逐字保留六条约束，尤其"原文没出现过的词，一个都不许写"）与 `USER_TEMPLATE`，把模块级函数改成协议对象：

```python
DEFAULT_TEXT_MODEL = "qwen-plus"
DEFAULT_OCR_MODEL = "qwen-vl-ocr"

# 提示词把模型当成不可靠的抄写员：只许摘录，不许补全，不许判断优先级。
SYSTEM_PROMPT = """你是小学作业文本结构化解析器。你的输出会被程序逐字核对原文，因此：

1. 所有字段值（subject/task/quantity/requirements/extras）必须【逐字摘录】原文，
   不得改写、补全、解释、合并或翻译。原文没出现过的词，一个都不许写。
2. 原文含糊、被截断、看不懂归属的片段，原样放进 unresolved，不要猜。
3. 不要输出 priority，优先级由程序按关键词判定，你写了也会被覆盖。
4. type 只能取 written/oral/reading/checkin/material 之一，判断不了就写 unknown。
5. estimated_minutes 是「建议值」，不确定就写 null，不要为了填满而编。
6. 只输出一个 JSON 对象，不要解释、不要代码块围栏。

输出 JSON 结构：
{"date": null, "items": [{"subject": "", "task": "", "quantity": "",
"requirements": [], "estimated_minutes": null, "type": "written"}],
"extras": [], "unresolved": []}"""

USER_TEMPLATE = """请把下面的老师作业原文解析成 JSON。日期为 {date}，学生姓名「{name}」。
再次强调：字段值必须是原文里能找到的字，找不到出处的内容请放进 unresolved。

原文：
\"\"\"{raw}\"\"\""""

OCR_SYSTEM_PROMPT = "你是 OCR 转写器，只输出图中文字原文。"
OCR_USER_TEXT = "按原样识别图片中的全部文字，保留原有编号、换行和符号，不要解释或补全。"


def _strip_fences(s: str) -> str:
    s = (s or "").strip()
    # 模型时而写 ```json 、时而写 ```JSON，大小写不定，一并剥。
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.S | re.I)
    return m.group(1) if m else s


class LlmExtractor:
    """原文 -> 候选结构（未经校验，不可直接上图）。

    transport 参数不是为了好看：它是让单元测试不打网络、
    而真正的调用质量留在 `-m network` 里由人工留证据。
    """

    def __init__(self, *, model: str = DEFAULT_TEXT_MODEL, transport=None) -> None:
        self.model = model
        self._transport = transport

    def __call__(self, raw_text: str, *, date: str = "", name: str = "") -> dict:
        # 传输层放到函数里 import：离线路径（NaiveExtractor）根本不碰网络模块。
        from homework_compass import llm_client as lc
        if not raw_text or not raw_text.strip():
            raise ExtractionError("作业原文为空。")
        text = lc.chat(
            [{"type": "text", "text": USER_TEMPLATE.format(
                date=date or "今天", name=name or "（未填）", raw=raw_text)}],
            self.model, system=SYSTEM_PROMPT,
            response_format={"type": "json_object"},   # 提示词已含 JSON，否则接口报错
            transport=self._transport,
        )
        try:
            parsed = json.loads(_strip_fences(text))
        except json.JSONDecodeError as e:
            raise ExtractionError(f"模型没返回合法 JSON：{text[:400]}") from e
        if not isinstance(parsed, dict):
            raise ExtractionError(f"模型返回的不是对象：{text[:200]}")
        return parsed


def ocr_to_text(image_path: Path, *, model: str = DEFAULT_OCR_MODEL, timeout: int = 120,
                transport=None) -> str:
    """截图/照片 -> 文本，之后进入与纯文本完全相同的解析+校验管线。

    它只返回文本：强制 OCR_UNVERIFIED 的责任在 validate(source_kind=SourceKind.OCR)，
    上游谁都不许自己放行。
    """
    from homework_compass import llm_client as lc
    if not image_path.is_file():
        raise ExtractionError(f"图片不存在：{image_path}")
    mime = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    content = [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        {"type": "text", "text": OCR_USER_TEXT},
    ]
    return lc.chat(content, model, system=OCR_SYSTEM_PROMPT, timeout=timeout,
                   transport=transport).strip()
```

`ocr_to_text` 只返回文本（system 换成「你是 OCR 转写器，只输出图中文字原文」，`temperature=0` 由 `chat` 统一设置）；强制 `OCR_UNVERIFIED` 的责任在 `validate(source_kind=SourceKind.OCR)`，不在这里——上游谁都不许自己放行。两步之外的 import（`base64` / `json` / `mimetypes` / `Path` / `ExtractionError`）追加到 `extract.py` 头部。

- [ ] **Step 4: 建网络测试目录并写真实冒烟（默认不跑）**

`tests/network/test_real_extract.py`：

```python
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
```

Run: `python3 -m pytest -q`
Expected: `114 passed, 1 deselected`（network 被默认 `-m 'not network'` 排除）；显式 `python3 -m pytest tests/network -m network -q` 需要 `DASHSCOPE_API_KEY` 与 `tests/fixtures/raw2.txt`（Task 18 建），由人工执行并把结果贴进 PR 描述。

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/llm_client.py src/homework_compass/parsing/extract.py tests/unit/test_llm_client.py tests/network/
git commit -m "feat: DashScope 传输层与 LLM/OCR extractor（key 只从环境变量读）"
```

---

## Task 11: 骨架坐标契约

**Files:**
- Create: `src/homework_compass/layout/__init__.py`
- Create: `src/homework_compass/layout/skeleton.py`
- Create: `tests/unit/test_skeleton.py`
- Reference: `poc/skeletons.py`（全文 156 行）

**Interfaces:**
- Consumes: 无（`layout.*` 不得 import `parsing.*`）
- Produces:

```python
A4_W: int = 2480 ; A4_H: int = 3508 ; A4_DPI: int = 300
MIN_MARGIN_PX: float                  # 10mm 换算到 300dpi
class ZoneKind(str, Enum): TITLE STATION EXTRAS REWARD
@dataclass(frozen=True, slots=True) class Zone: key kind x y w h px role  -> .rect
@dataclass(frozen=True, slots=True) class Skeleton: name cn_name desc zones -> .stations
def quest_map(n_stations: int = 6) -> Skeleton
SKELETONS: dict[str, Callable[[], Skeleton]]
def get_skeleton(name: str) -> Skeleton          # 未知名字 → ValueError，不是 KeyError
def skin_palette(skin: str) -> dict[str, str]
def build_prompt(skeleton: Skeleton, skin: str) -> str
def zones_report(skeleton: Skeleton) -> str
```

- [ ] **Step 1: 写失败测试**

```python
import inspect

import pytest

from homework_compass.layout.skeleton import (
    A4_DPI, A4_H, A4_W, MIN_MARGIN_PX, SKELETONS, Zone, ZoneKind,
    build_prompt, get_skeleton, quest_map, skin_palette, zones_report,
)


def px(v: float, axis: str) -> float:
    return v * (A4_W if axis == "x" else A4_H)


def test_a4_constants_are_exactly_as_spec():
    assert (A4_W, A4_H, A4_DPI) == (2480, 3508, 300)


def test_quest_map_has_six_stations_and_one_extras():
    """poc 实测：6 个关卡位 + 1 条易漏项带，超过 6 项必须换骨架或分页。"""
    sk = quest_map()
    assert len(sk.stations) == 6
    assert [z.px for z in sk.stations] == [1, 2, 3, 4, 5, 6]
    assert sum(1 for z in sk.zones if z.kind is ZoneKind.EXTRAS) == 1


def test_every_zone_respects_ten_mm_margin():
    """spec §6.3：边距不达标要在骨架构造期就失败，不靠人记。"""
    sk = quest_map()
    for z in sk.zones:
        assert px(z.x, "x") >= MIN_MARGIN_PX, z.key
        assert px(1 - z.x - z.w, "x") >= MIN_MARGIN_PX, z.key
        assert px(z.y, "y") >= MIN_MARGIN_PX, z.key
        assert px(1 - z.y - z.h, "y") >= MIN_MARGIN_PX, z.key


def test_out_of_margin_zone_raises_at_construction():
    with pytest.raises(ValueError, match="页边距"):
        Zone("bad", ZoneKind.STATION, 0.01, 0.5, 0.4, 0.1, px=1)


def test_zones_do_not_overlap_each_other():
    sk = quest_map()
    rects = [z.rect for z in sk.zones]
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (a, b)


def test_rect_is_normalized_to_pixels():
    z = Zone("t", ZoneKind.TITLE, 0.08, 0.035, 0.84, 0.072, role="标题")
    l, t, r, b = z.rect
    assert (l, t) == (round(0.08 * A4_W), round(0.035 * A4_H))
    assert r > l and b > t


def test_station_count_bounds():
    # 6 是几何上限：第 7 关会撞上易漏项带并破 10mm 边距（poc 曾允许到 8，但会画到纸外）。
    for n in (0, 2, 7, 8, 9):
        with pytest.raises(ValueError):
            quest_map(n)


def test_registry_is_pure_data_extension_point():
    assert set(SKELETONS) == {"quest-map"}
    assert SKELETONS["quest-map"]() .name == "quest-map"


# ---- build_prompt：单一事实来源不变量的另一半，本版不调用但必须留在库里 ----

def test_prompt_describes_every_zone_spatially():
    sk = quest_map()
    p = build_prompt(sk, "dinosaur")
    for z in sk.zones:
        assert f"{round(z.x * 100, 1)}%" in p
        assert f"{round((z.y + z.h) * 100, 1)}%" in p


def test_prompt_forbids_any_text_in_boxes():
    p = build_prompt(quest_map(), "space")
    assert "框内不得绘制任何文字" in p
    assert "汉字" in p and "水印" in p


def test_prompt_never_receives_homework_text():
    """签名里只有骨架与皮肤——做不到「不传文字」就是契约失效。"""
    params = list(inspect.signature(build_prompt).parameters)
    assert params == ["skeleton", "skin"]


def test_prompt_mentions_station_count():
    assert "6 个关卡框" in build_prompt(quest_map(), "dinosaur")


def test_skin_palette_always_has_accent():
    assert skin_palette("nonexistent")["accent"].startswith("#")


def test_unknown_skeleton_name_is_a_loud_error():
    """退出码契约要求「未知骨架」是 4，不是一个漂进终端的 KeyError。"""
    with pytest.raises(ValueError, match="quest-map"):
        get_skeleton("nope")


def test_known_name_returns_the_skeleton():
    assert get_skeleton("quest-map").name == "quest-map"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_skeleton.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 skeleton.py**

以 `poc/skeletons.py` 为基准移植，五处正式化：

1. `ZoneKind` 由裸字符串升级为 `str, Enum`（`kind` 比较用 `is ZoneKind.STATION`）。
2. `Zone.__post_init__` 做页边距断言（poc 完全没有这道校验，靠人核对）：

```python
# 10mm 换算到 300dpi：10 / 25.4 * 300 ≈ 118.1px。spec §6.3 的硬底线。
MIN_MARGIN_PX = 10 * A4_DPI / 25.4


@dataclass(frozen=True, slots=True)
class Zone:
    key: str
    kind: ZoneKind
    x: float
    y: float
    w: float
    h: float
    px: int = 0
    role: str = ""

    def __post_init__(self) -> None:
        # 页边距在构造期就查：靠人核对坐标表迟早会漂，漂到打印纸上才发现。
        if self.x < 0 or self.y < 0:
            raise ValueError(f"{self.key}: 坐标越界（x={self.x}, y={self.y}）")
        for axis, pos, size, span in (("x", self.x, self.w, A4_W),
                                      ("y", self.y, self.h, A4_H)):
            for edge, dist in (("起始", pos), ("结束", 1.0 - pos - size)):
                if dist * span < MIN_MARGIN_PX:
                    raise ValueError(
                        f"{self.key}: {axis} {edge}页边距 {round(dist * span)}px "
                        f"低于 10mm（{round(MIN_MARGIN_PX)}px）要求")

    @property
    def rect(self) -> tuple[int, int, int, int]:
        return (round(self.x * A4_W), round(self.y * A4_H),
                round((self.x + self.w) * A4_W), round((self.y + self.h) * A4_H))
```

报错文案必须带「页边距」三个字：`test_out_of_margin_zone_raises_at_construction` 用 `match="页边距"` 锁它，写成「起始边距」测试当场失败。

3. `Skeleton.stations` 按 `px` 排序返回（同 poc）。`n_stations` 边界收到 **3–6**：poc 虽写了 3–8，但 7 关起最后一排就跑到纸外（`0.135 + 6*0.126 + 0.112 > 1`），只是 poc 没有边距校验才没人发现；spec §6.1 只要 6 个关卡位，§6.3 要求项数超限报错而不是静默截断。边界必须与 `Zone` 的页边距断言自洽：

```python
    if not 3 <= n_stations <= 6:
        raise ValueError(
            "quest-map 只放得下 3-6 个关卡：第 6 关底边 87.7% 已经贴着易漏项带"
            "（90.5%），再加一排就破 10mm 页边距。更多项请换骨架或分页（spec §6.3）。")
```

4. `build_prompt` / `skin_palette` / `zones_report` 逐字移植，坐标百分比与 `skeleton.cn_name/desc` 一律由参数拼装，不写死。`zones_report` 里 `kind` 已是枚举，格式化要用 `z.kind.value`，否则打印出 `ZoneKind.STATION` 且列宽对不齐。
5. 新增 `get_skeleton(name)`，把注册表查表的 `KeyError` 翻译成带可选值的 `ValueError`：

```python
def get_skeleton(name: str) -> Skeleton:
    """所有外部输入的骨架名都走这里，不直接 `SKELETONS[...]`。

    CLI 退出码契约里 4 = 参数错误；KeyError 会被当成意外崩溃，
    既进不了 except 分支，也告诉不了人到底能用什么。"""
    try:
        return SKELETONS[name]()
    except KeyError:
        raise ValueError(f"未知骨架 {name!r}，可选：{sorted(SKELETONS)}") from None
```

6. 模块 docstring 必须把不变量写全：

```python
"""版式骨架：留白区的归一化坐标是本文件唯一的事实来源。

生图提示词由这些坐标自动拼装，Pillow 文字层读同一批坐标，
因此「AI 画出来的框」和「我们写字的位置」物理上不可能对不上——
这是双层架构最大的风险点（留白与落位漂移）的结构性解法。

build_prompt 在本版没有被任何生产路径调用，但绝不能删：它就是上述不变量的
另一半。删掉它，坐标契约退化成「只有文字层用得上的坐标表」，
接生图的那个 spec 必然另写一份提示词，契约当场失效。
"""
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_skeleton.py -q`
Expected: `15 passed`（全量 `129 passed`）

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/layout/ tests/unit/test_skeleton.py
git commit -m "feat: 骨架坐标契约（含 10mm 边距构造期断言与提示词构建）"
```

---

## Task 12: 字体解析与字形覆盖探针

**Files:**
- Create: `src/homework_compass/layout/fonts.py`
- Create: `tests/unit/test_fonts.py`
- Reference: `poc/compose.py:17-54`（回退链与缓存）

**Interfaces:**
- Consumes: `errors.FontError`
- Produces:

```python
DEFAULT_CANDIDATES: list[str]
SAMPLE_GLYPHS: str                     # 探针用汉字
def resolve_font_path(candidates: Sequence[str] | None = None) -> str
def check_glyph_coverage(f: ImageFont.FreeTypeFont, samples: str = SAMPLE_GLYPHS) -> None
def load_font(px: int, *, path: str | None = None) -> ImageFont.FreeTypeFont
def clear_cache() -> None
```

poc 只靠"文件存在"碰运气，实测本机 `PingFang.ttc` 在 macOS 26 已不存在，全靠 `Hiragino Sans GB` 兜住才没露馅。正式版必须真的把字画出来看一眼。

- [ ] **Step 1: 写失败测试**

```python
import sys
from pathlib import Path

import pytest
from PIL import ImageFont

from homework_compass.errors import FontError
from homework_compass.layout.fonts import (
    check_glyph_coverage, clear_cache, load_font, resolve_font_path,
)

pytestmark = pytest.mark.skipif(sys.platform != "darwin",
                                reason="候选表是 macOS 系统字体路径")

ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def test_resolve_finds_a_real_cjk_font():
    p = resolve_font_path()
    assert p and Path(p).is_file()


def test_loaded_font_is_at_least_requested_size():
    f = load_font(50)
    assert f.size == 50


def test_probe_passes_on_real_chinese():
    check_glyph_coverage(load_font(60))          # 不抛就是通过


def test_probe_rejects_font_without_the_sample_glyph():
    """豆腐块/空白必须被抓出来：poc 靠回退链碰运气，本机 PingFang 已不存在。"""
    fake = ImageFont.truetype(ARIAL, 60)
    with pytest.raises(FontError, match="字形覆盖"):
        check_glyph_coverage(fake)


def test_all_candidates_missing_raises_with_tried_paths(monkeypatch):
    from homework_compass.layout import fonts
    monkeypatch.setattr(fonts.Path, "is_file", lambda self: False)
    with pytest.raises(FontError, match="已尝试"):
        resolve_font_path(["/nonexistent/x.ttf"])


def test_cache_is_per_size_and_can_be_cleared():
    clear_cache()
    a, b = load_font(40), load_font(40)
    assert a is b
    clear_cache()
    assert load_font(40) is not a


def test_resolve_skips_existing_font_without_cjk():
    """路径存在不代表能画中文：Arial 存在但缺汉字，必须跳过而不是选中后炸掉。"""
    assert resolve_font_path([ARIAL, CJK]) == CJK


def test_only_bad_candidates_list_each_reason():
    with pytest.raises(FontError, match="字形覆盖"):
        resolve_font_path([ARIAL])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_fonts.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 fonts.py**

```python
"""字体解析 + 字形覆盖探针。

只做「文件存在」检查是不够的：路径存在不代表它能画中文，
缺字时 Pillow 会安静地画出豆腐块或空白，图上看不出来、程序不报错，
直到打印出来才发现整张纸缺了「签字」两个字。
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PIL import ImageFont

from homework_compass.errors import FontError

DEFAULT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",                 # macOS 14 及更早
    "/System/Library/Fonts/Hiragino Sans GB.ttc",         # macOS 26 实测可用
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    # 非 macOS 常见路径：Linux 发行版与 CI 镜像
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

# 探针取日常作业里真会出现的字，不是 "abcdefghijklmnopqrstuvwxyz"。
# 「签」「卡」「册」这类字最容易被供应商字体子集化掉。
SAMPLE_GLYPHS = "今日作业数学语文英语练习册家长签字打卡彩泥剪刀"

# 解析期探针字号：够大能看出豆腐块，又不必按目标字号渲染。
PROBE_PX = 40


def resolve_font_path(candidates: Sequence[str] | None = None) -> str:
    tried = list(candidates) if candidates else list(DEFAULT_CANDIDATES)
    for p in tried:
        if Path(p).is_file():
            return p
    raise FontError(
        "找不到可用的中文字体，无法保证「正文≥14pt 清晰可读」。已尝试：" + "、".join(tried)
    )


def _bitmap(f: ImageFont.FreeTypeFont, ch: str) -> tuple[tuple[int, int], bytes]:
    mask = f.getmask(ch, mode="L")
    return mask.size, bytes(mask)


def check_glyph_coverage(f: ImageFont.FreeTypeFont, samples: str = SAMPLE_GLYPHS) -> None:
    """两个判据：墨迹非空；不同汉字不能画出一模一样的东西（豆腐块的特征）。"""
    for ch in samples:
        size, data = _bitmap(f, ch)
        if not size or not size[0] or not size[1] or not any(data):
            raise FontError(
                f"字形覆盖探针失败：字体不覆盖「{ch}」（渲染结果空白），无法出图。")
    first = _bitmap(f, samples[0])[1]
    for ch in samples[1:]:
        if _bitmap(f, ch)[1] == first:
            raise FontError(
                f"字形覆盖探针失败：「{ch}」与「{samples[0]}」渲染完全相同，"
                "几乎可以断定是 .notdef 豆腐块。请更换字体。")


def resolve_font_path(candidates: Sequence[str] | None = None) -> str:
    """按优先级挑第一个「真的能画中文」的字体，不是第一个存在的文件。

    回退链里混进一个缺汉字的字体时（路径存在、渲染是豆腐块），
    直接返回它会让 load_font 当场炸掉，明明下一个候选是好的。
    """
    tried = list(candidates) if candidates else list(DEFAULT_CANDIDATES)
    problems: list[str] = []
    for p in tried:
        if not Path(p).is_file():
            problems.append(f"{p}（不存在）")
            continue
        try:
            check_glyph_coverage(ImageFont.truetype(p, size=PROBE_PX))
        except (FontError, OSError) as e:
            problems.append(f"{p}（{e}）")
            continue
        return p
    raise FontError(
        "找不到可用的中文字体，无法保证「正文≥14pt 清晰可读」。已尝试：" + "、".join(problems))


_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
# 默认字体解析一次就够：resolve 会真的加载字体试渲染，每次 load_font 重跑它
# 等于每取一个字号就多花一次字体加载。clear_cache() 时一并复位。
_DEFAULT_PATH: str | None = None


def load_font(px: int, *, path: str | None = None) -> ImageFont.FreeTypeFont:
    global _DEFAULT_PATH
    px = max(int(px), 8)
    if path is None:
        _DEFAULT_PATH = _DEFAULT_PATH or resolve_font_path()
        path = _DEFAULT_PATH
    key = (path, px)
    if key not in _CACHE:
        f = ImageFont.truetype(path, size=px)
        check_glyph_coverage(f)      # 指定 path 时绕过了 resolve，这里补一次
        _CACHE[key] = f
    return _CACHE[key]


def clear_cache() -> None:
    """测试与配置变更用；生产代码不该调它。"""
    global _DEFAULT_PATH
    _DEFAULT_PATH = None
    _CACHE.clear()
```

三处与 brief 原稿不同，都是为了兑现 spec §6.4 的「**全部失败**则抛 FontError 并列出已尝试路径」：① `resolve_font_path` 不再「文件存在就返回」，而是真的加载试渲染，缺汉字的候选被跳过（否则回退链形同虚设）；② 两条探针报错都带「字形覆盖」字样（测试用 `match="字形覆盖"`，原稿的「字体不覆盖字形」匹配不上）；③ `load_font` 缓存解析结果，否则每取一个字号都要重新加载一遍 23MB 的 TTC（实测 20 次命中从 77ms 降到 0.01ms）。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_fonts.py -q`
Expected: `8 passed`（全量 `137 passed`）。若 `test_probe_rejects_font_without_the_sample_glyph` 在本机通过不了（Arial 意外覆盖了中文），改用确实不含汉字的字体路径，但**不得删掉这条测试**——它是本任务的全部意义。

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/layout/fonts.py tests/unit/test_fonts.py
git commit -m "feat: 字体解析与字形覆盖探针（不再靠回退链碰运气）"
```

---

## Task 13: 文字层排版

**Files:**
- Create: `src/homework_compass/layout/compose.py`
- Create: `tests/unit/test_compose_layout.py`
- Reference: `poc/compose.py:36-186`（尺寸换算、折行、缩放）、`poc/compose.py:188-314`（五个绘制函数）

**Interfaces:**
- Consumes: `layout.skeleton`、`layout.fonts`、`models.ParsedHomework / RenderIssue`、`errors.LayoutError`
- Produces:

```python
BODY_PT: float = 14.0 ; NOTE_PT: float = 10.0 ; TITLE_PT: float = 28.0
BODY_FLOOR_PT: float = 12.0
LINE_GAP: float = 1.28 ; NO_LINE_START: str
def pt_to_px(pt: float) -> int
def text_w(s: str, f) -> float
def wrap(text: str, f, max_w: float) -> list[str]
def fit_block(text, max_w, max_h, base_px, floor_px, line_gap=1.28) -> tuple[list[str], int, float]
def body_px_for(zone_h: int) -> int
def station_text(item: HomeworkItem) -> tuple[str, list[str]]
def draw_zone_guides(img: Image.Image, skeleton: Skeleton) -> None
def placeholder_base(skeleton: Skeleton) -> Image.Image
def upscale_to_a4(base: Image.Image) -> Image.Image
def compose(hw: ParsedHomework, skeleton: Skeleton, *, skin: str = "dinosaur",
            base: Image.Image | None = None,
            panel_alpha: int = 190) -> tuple[Image.Image, list[RenderIssue]]
```

`layout.*` 不碰文件系统、不碰 tty——返回图像，落盘由 `pipeline` 负责。

- [ ] **Step 1: 写失败测试（测不变量，不测像素）**

`tests/unit/test_compose_layout.py`：

```python
import sys

import pytest
from PIL import Image

from homework_compass.errors import LayoutError
from homework_compass.layout.compose import (
    BODY_PT, BODY_FLOOR_PT, NO_LINE_START, body_px_for, compose, fit_block,
    placeholder_base, pt_to_px, station_text, upscale_to_a4, wrap,
)
from homework_compass.layout.fonts import load_font
from homework_compass.layout.skeleton import A4_H, A4_W, quest_map
from homework_compass.models import (
    HomeworkItem, ParsedHomework, SourceKind, TraceLevel, ValidationReport,
)

pytestmark = pytest.mark.skipif(sys.platform != "darwin",
                                reason="候选表是 macOS 系统字体路径")

SK = quest_map()


def item(seq, task, qty="", reqs=(), priority="normal"):
    return HomeworkItem(seq=seq, subject="数学", task=task, quantity=qty,
                        requirements=list(reqs), requirements_all=list(reqs),
                        priority=priority, priority_signals=[], estimated_minutes=None,
                        type="written",
                        provenance={"task": TraceLevel.VERBATIM,
                                    "quantity": TraceLevel.VERBATIM,
                                    "subject": TraceLevel.VERBATIM})


def hw(items, extras=()):
    return ParsedHomework(date="2026-11-06", student_name="小宇", slogan="今日目标",
                          items=list(items), extras=list(extras), pending=[],
                          source_text="原文", source_kind=SourceKind.TEXT,
                          report=ValidationReport())


def white():
    return Image.new("RGB", (A4_W, A4_H), "#FFFFFF")


def test_canvas_is_a4_before_any_text_is_drawn():
    """顺序不可颠倒：先超分再写字，反过来文字发虚，直接违反验收口径。"""
    small = Image.new("RGB", (600, 800), "#FFFFFF")
    assert upscale_to_a4(small).size == (A4_W, A4_H)
    img, _ = compose(hw([item(1, "练习册", "P12-13")]), SK, base=small)
    assert img.size == (A4_W, A4_H)


def test_more_items_than_stations_raises_not_truncates():
    sk = quest_map(3)
    with pytest.raises(LayoutError, match="骨架"):
        compose(hw([item(i, "练习册") for i in range(1, 5)]), sk, base=white())


def test_no_line_start_rules_apply():
    """标点不能孤零零落到行首：换行时把前一个字一起带下来。"""
    for ch in ("）", "。", "！", "、"):
        assert ch in NO_LINE_START
    lines = wrap("抄写本课生字（每个两）", load_font(40), 10 * 40)
    assert len(lines) == 2
    assert lines[1] == "两）"          # 若去掉禁则，「）」会自己起一行
    assert all(not any(ln.startswith(ch) for ch in NO_LINE_START) for ln in lines)


def test_body_floor_is_reported_not_silently_truncated():
    long = "抄写本课生字每个两遍并注音" * 12
    img, issues = compose(hw([item(1, long)]), SK, base=white())
    assert issues            # 一定有话说，绝不静默
    assert any("14pt" in i.reason or "放不下" in i.reason for i in issues)


def test_empty_stations_are_marked():
    img, issues = compose(hw([item(1, "练习册")]), SK, base=white())
    assert issues == []      # 空关卡是正常版面，不是问题


def test_requirement_already_in_task_is_not_printed_twice():
    """回归：poc 实测「家长签字」在卡面上印了两遍。

    校验层会去重，但旧 hw.json 没有经过校验层（模型层承诺兼容 poc JSON），
    印在纸上的重复收不回来，所以排版层自己再挡一次。
    """
    task, reqs = station_text(item(1, "完成练习册，家长签字", "", ["家长签字", "用铅笔"]))
    assert reqs == ["用铅笔"]
    assert task.count("家长签字") == 1


def test_placeholder_base_is_a4_and_untouched_by_items():
    p = placeholder_base(SK)
    assert p.size == (A4_W, A4_H)


def test_body_px_floor():
    assert pt_to_px(14) == round(14 * 300 / 72)


def test_body_px_for_caps_at_design_size_and_flags_short_zones():
    """可用高度再大，正文也不会超过 14pt 的设计值；矮到装不下一行时如实小于下限。"""
    assert body_px_for(10_000) == pt_to_px(BODY_PT)
    assert body_px_for(30) < pt_to_px(BODY_FLOOR_PT)


def test_fit_block_does_not_shrink_when_text_already_fits():
    lines, px, lh = fit_block("练习册", 800, 400, pt_to_px(BODY_PT), pt_to_px(BODY_FLOOR_PT))
    assert lines == ["练习册"]
    assert px == pt_to_px(BODY_PT)
    assert lh == round(px * 1.28)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/unit/test_compose_layout.py -q`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 compose.py**

以 `poc/compose.py` 为基准移植全部绘制逻辑（`_panel` / `_star` / `_round_rect` / `_draw_title` / `_draw_station` / `_empty_station` / `_draw_extras` / `_draw_reward`），六处正式化：

1. 字体走 `fonts.load_font`，删掉本地 `FONT_CANDIDATES` 与 `resolve_font_path`；`FontError` 原样上抛（可操作信息比吞掉有用）。
2. 异常换 `LayoutError`；项数超留白时文案保留 poc 的"需分页或换骨架"提示。
3. 入口断言画布：`compose()` 第一步就是 `canvas = upscale_to_a4(base if base is not None else placeholder_base(skeleton)).copy()`，并在其后加 `assert canvas.size == (A4_W, A4_H)`（用 `is not None` 而不是 `or`：图像的真值判断没有语义，显式比较才看得出来基线是可选参数）。
4. `data: dict` 换成 `hw: ParsedHomework`，读取用属性而非 `.get()`；`priority` 用 `it.priority == "high"`。正文与要求经 `station_text(item)` 组装：数量跟在任务后，与任务重复的要求不再单列（理由见下）。
5. poc 的 `placeholder_base()` 里有一行没用的 `d = ImageDraw.Draw(img)`，删；同时把它接上 `draw_zone_guides`，让占位图自带留白框，肉眼可核对对位。
6. 新增 `body_px_for(zone_h: int) -> int`：给定正文可用高度，返回首行放得下的最大正文字号（px），上限 `pt_to_px(BODY_PT)`；只做几何换算，不替人判断「这么小还能不能读」——低于 `pt_to_px(BODY_FLOOR_PT)` 时由 `compose` 追加 `RenderIssue`。

`wrap` / `fit_block` / `NO_LINE_START` 逐字移植（含 poc 已验证的换行禁则：标点会把前一个字一起带下来）。

**本版对 poc 的第二处刻意改进（会体现在 Task 18 平价差异里）**：poc 的 `_draw_station` 把 `requirements` 原样印出来，`poc/out/hw_raw1.json` 的三个关卡各多印一行——「用铅笔」「家长检查后签字」「书写工整」「APP打卡」全都已经写在 task 句子里。校验层（Task 6）已去过一次重，但 `models.from_json` 承诺兼容 poc 时代的 hw.json，那条路径没有这道保证，而印在纸上的重复收不回来，所以 `station_text` 再挡一次。探针实测：同一份 hw_raw1，poc 与新版出图相差 10330 px、全部落在第 1–3 关正文区，正是被去掉的那四行；`hw_raw2.json`（要求均不在任务里）逐像素相同。理由：重复印刷是可看见的错，宁可排版层多一道过滤。

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_compose_layout.py -q`
Expected: `10 passed`（全量 `147 passed`）

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/layout/compose.py tests/unit/test_compose_layout.py
git commit -m "feat: Pillow 文字层排版（画布尺寸断言 + 字号下限上报）"
```

---

## Task 14: 配置加载

**Files:**
- Create: `src/homework_compass/config.py`
- Create: `tests/unit/test_config.py`
- Modify: `src/homework_compass/errors.py`（追加 `ConfigError`）

**Interfaces:**
- Consumes: `stdlib tomllib`、`os.environ`
- Produces:

```python
@dataclass(frozen=True, slots=True)
class Config:
    name: str; default_skeleton: str; default_skin: str
    text_model: str; ocr_model: str; fonts: tuple[str, ...]; out_dir: Path

def load_config(root: Path | None = None) -> Config
def load_profile(root: Path | None = None) -> dict
def load_dotenv_default(root: Path | None = None) -> None
DEFAULTS: dict
```

**结构性约束（spec §7.4）**：`Config` 里**不存在** `api_key` 字段，全库没有任何从 `config.toml`/`profile.toml` 读取 `DASHSCOPE_API_KEY` 的代码路径。不是"建议不要写"，是写了也没人读——本任务用测试把这句话钉住。

- [ ] **Step 1: 写失败测试**

```python
from pathlib import Path

import pytest

from homework_compass.config import (
    Config, DEFAULTS, load_config, load_dotenv_default, load_profile,
)


def write(root: Path, name: str, text: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text, encoding="utf-8")


def test_defaults_when_no_files(tmp_path):
    c = load_config(tmp_path)
    assert c.default_skeleton == "quest-map" and c.text_model == "qwen-plus"
    assert c.out_dir == Path(DEFAULTS["out_dir"]) and c.fonts == ()


def test_config_toml_is_read(tmp_path):
    write(tmp_path, "config.toml", 'text_model = "qwen-plus"\nout_dir = "build/out"\n')
    assert load_config(tmp_path).out_dir == Path("build/out")


def test_profile_overrides_config(tmp_path):
    write(tmp_path, "config.toml", 'name = "配置里的人"\n')
    write(tmp_path, "profile.toml", 'name = "小宇"\ndefault_skin = "space"\n')
    c = load_config(tmp_path)
    assert c.name == "小宇" and c.default_skin == "space"


def test_env_wins_over_files(tmp_path, monkeypatch):
    write(tmp_path, "profile.toml", 'name = "小宇"\n')
    monkeypatch.setenv("HW_NAME", "环境变量的人")
    assert load_config(tmp_path).name == "环境变量的人"


def test_unknown_key_is_a_loud_error_not_typo_silence(tmp_path):
    write(tmp_path, "config.toml", 'text_modle = "qwen-plus"\n')   # 手滑打错
    from homework_compass.errors import ConfigError
    with pytest.raises(ConfigError, match="text_modle"):
        load_config(tmp_path)


def test_invalid_toml_is_reported_with_path(tmp_path):
    write(tmp_path, "config.toml", "name = 小宇\n")                 # 少引号
    from homework_compass.errors import ConfigError
    with pytest.raises(ConfigError, match="config.toml"):
        load_config(tmp_path)


def test_credentials_cannot_be_configured():
    """凭证不属配置体系：既没有承载它的字段，也没有读它的代码路径。

    本任务全部意义就在这条：只要 `Config` 里没有 `api_key` 这种字段，
    「把 key 写进 config.toml 然后提交」这件事在结构上就无法发生。
    """
    import homework_compass.config as cfg
    assert not any("api_key" in f.lower() or "token" in f.lower()
                   for f in Config.__slots__)
    assert not hasattr(cfg, "api_key")
    text = Path(cfg.__file__).read_text(encoding="utf-8")
    # docstring 里提到变量名是允许的（它是说明），被禁止的是真的去读它
    assert 'environ.get("DASHSCOPE_API_KEY")' not in text
    assert 'getenv("DASHSCOPE_API_KEY")' not in text


def test_dotenv_sets_env_without_overwriting(tmp_path, monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    write(tmp_path, ".env", "DASHSCOPE_API_KEY=sk-from-file\n")
    load_dotenv_default(tmp_path)
    import os
    assert os.environ["DASHSCOPE_API_KEY"] == "sk-from-file"
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-real")
    load_dotenv_default(tmp_path)
    assert os.environ["DASHSCOPE_API_KEY"] == "sk-real"       # setdefault 语义


def test_dotenv_skips_comments_blank_and_non_assignments(tmp_path, monkeypatch):
    monkeypatch.delenv("HW_SKIN", raising=False)
    write(tmp_path, ".env", "# 注释\n\n不是赋值\nHW_SKIN = 'ocean'\n")
    load_dotenv_default(tmp_path)
    import os
    assert os.environ["HW_SKIN"] == "ocean"      # 去空格、去引号


def test_fonts_as_string_is_rejected_not_split_into_chars(tmp_path):
    """`fonts = "/path/a.ttc"` 会被 tuple() 拆成一个个字符，报错比二十条假路径强。"""
    write(tmp_path, "config.toml", 'fonts = "/System/Library/Fonts/PingFang.ttc"\n')
    from homework_compass.errors import ConfigError
    with pytest.raises(ConfigError, match="fonts"):
        load_config(tmp_path)


def test_wrong_value_type_is_rejected_with_field_name(tmp_path):
    write(tmp_path, "config.toml", "name = 123\n")
    from homework_compass.errors import ConfigError
    with pytest.raises(ConfigError, match="name"):
        load_config(tmp_path)


def test_fonts_from_toml_become_a_tuple(tmp_path):
    write(tmp_path, "config.toml", 'fonts = ["/a.ttc", "/b.ttc"]\n')
    assert load_config(tmp_path).fonts == ("/a.ttc", "/b.ttc")


def test_load_profile_missing_file_is_empty_dict(tmp_path):
    assert load_profile(tmp_path) == {}
```

Run: `python3 -m pytest tests/unit/test_config.py -q`
Expected: `ModuleNotFoundError: No module named 'homework_compass.config'`

- [ ] **Step 2: 实现 config.py**

```python
"""配置：命令行 > 环境变量 > config.toml / profile.toml > 内置默认。

环境变量前缀统一 HW_（HW_NAME / HW_SKELETON / HW_SKIN / HW_OUT / HW_TEXT_MODEL /
HW_OCR_MODEL）。凭证不在此列：DASHSCOPE_API_KEY 只由 llm_client 从环境读取，
本模块不认识它。把密钥做成一个「配置字段」，下一步就是它被写进 config.toml
然后提交——那一步不该有路可走。

out_dir 保持用户写下的样子（相对路径按调用时的 cwd 解释），本模块不替人猜根目录。
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from homework_compass.errors import ConfigError

DEFAULTS: dict = {
    "name": "",
    "default_skeleton": "quest-map",
    "default_skin": "dinosaur",
    "text_model": "qwen-plus",
    "ocr_model": "qwen-vl-ocr",
    "fonts": (),
    "out_dir": "out",
}

_ENV_MAP = {"HW_NAME": "name", "HW_SKELETON": "default_skeleton",
            "HW_SKIN": "default_skin", "HW_OUT": "out_dir",
            "HW_TEXT_MODEL": "text_model", "HW_OCR_MODEL": "ocr_model"}

_STRING_FIELDS = frozenset(DEFAULTS) - {"fonts", "out_dir"}


@dataclass(frozen=True, slots=True)
class Config:
    name: str
    default_skeleton: str
    default_skin: str
    text_model: str
    ocr_model: str
    fonts: tuple[str, ...]
    out_dir: Path


def _read_toml(path: Path, known: dict, label: str) -> dict:
    if not path.is_file():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path} 不是合法 TOML：{e}") from e
    unknown = set(data) - set(known)
    if unknown:
        # 打错的键静默失效比报错更糟：用户以为自己配置好了
        raise ConfigError(f"{label} 不认识这些键：{sorted(unknown)}；可用键：{sorted(known)}")
    return data


def load_profile(root: Path | None = None) -> dict:
    """姓名 / 默认骨架 / 默认皮肤。方案文档的「一次设置、长期复用」，纯文件不引数据库。"""
    base = Path(root) if root else Path.cwd()
    return _read_toml(base / "profile.toml", DEFAULTS, "profile.toml")


def load_config(root: Path | None = None) -> Config:
    base = Path(root) if root else Path.cwd()
    merged = dict(DEFAULTS)
    merged.update(_read_toml(base / "config.toml", DEFAULTS, "config.toml"))
    merged.update(load_profile(base))
    for env, field in _ENV_MAP.items():
        if os.environ.get(env):
            merged[field] = os.environ[env]
    _check_types(merged)
    return Config(**{**merged, "out_dir": Path(merged["out_dir"]),
                     "fonts": tuple(merged["fonts"])})


def _check_types(merged: dict) -> None:
    """值类型错了也当场报错：`name = 123` 要等到拼标题时才炸，那时已经出了半张图。"""
    for field in sorted(_STRING_FIELDS):
        if not isinstance(merged[field], str):
            raise ConfigError(
                f"{field} 必须是字符串，读到 {type(merged[field]).__name__}：{merged[field]!r}")
    fonts = merged["fonts"]
    # `fonts = "/path/a.ttc"` 会被 tuple() 拆成一个个字符，解析字体时给出二十条假路径
    if isinstance(fonts, str) or not isinstance(fonts, (list, tuple)):
        raise ConfigError(
            f"fonts 要写成数组：fonts = [\"/path/a.ttc\", …]；读到 {type(fonts).__name__}：{fonts!r}")
    if not isinstance(merged["out_dir"], (str, Path)):
        raise ConfigError(f"out_dir 必须是字符串路径，读到 {type(merged['out_dir']).__name__}")


def load_dotenv_default(root: Path | None = None) -> None:
    """把 .env 灌进环境变量（已存在的不覆盖）。

    这仍然算「只从环境读取」：`.env` 是被 .gitignore 排除的环境载体，
    而不是配置体系里的一个字段——它承载的 key 照样进不了 Config。
    """
    candidate = (Path(root) if root else Path.cwd()) / ".env"
    if not candidate.is_file():
        return
    for raw in candidate.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip():
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
```

`errors.py` 追加：

```python
class ConfigError(HomeworkError):
    """配置文件不合法或含未知键。未知键必须报错，不能静默忽略。"""
```

**为什么还要查值类型**：`_read_toml` 只挡未知键，不管类型。`fonts = "/a.ttc"`（字符串而不是数组）会在 `tuple()` 里被拆成一个个字符，解析字体时给出二十条单字符路径；`name = 123` 一路活到 `compose` 拼标题时才 TypeError——那时图已经画了一半。配置是唯一进得来人手写内容的地方，进门前把类型核完：报告里带字段名与读到的值，比堆栈有用。

- [ ] **Step 3: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_config.py -q`
Expected: `13 passed`（全量 `160 passed`）

- [ ] **Step 4: Commit**

```bash
git add src/homework_compass/config.py src/homework_compass/errors.py tests/unit/test_config.py
git commit -m "feat: 配置优先级（toml/env/默认）与凭证不可配置化"
```

---

## Task 15: 对外 API 编排层

**Files:**
- Create: `src/homework_compass/pipeline.py`
- Modify: `src/homework_compass/__init__.py`（填 public 导出）
- Create: `tests/unit/test_pipeline.py`

**Interfaces:**
- Consumes: `parsing.extract / parsing.validate / layout.skeleton / layout.compose / config / models / errors`
- Produces:

```python
def parse_homework(raw_text: str, *, extractor: Extractor | None = None,
                   date: str = "", name: str = "",
                   source_kind: SourceKind = SourceKind.TEXT) -> ParsedHomework
def correct(hw, seq: int, field: str, value: str) -> ParsedHomework      # 转发
def dismiss(hw, pending_id: str) -> ParsedHomework                        # 转发
def render(hw, *, skeleton: str = "quest-map", skin: str = "dinosaur",
           base: Path | None = None, out_dir: Path = Path("out"),
           panel_alpha: int = 190,
           fonts: Sequence[str] | None = None) -> RenderResult  # pending 非空抛 NeedsConfirmation
def save_hw(hw, path: Path) -> Path
def load_hw(path: Path) -> ParsedHomework
def text_from_image(image: Path, *, model: str | None = None) -> tuple[str, SourceKind]
```

`fonts` 是 spec §6.4.1「候选表可被配置覆盖」的落点：透传给 `layout.compose`，`None` 时走 `layout.fonts` 的默认候选表。没有这个参数，配置里的 `fonts` 就是死配置。

`pipeline` 只做编排：函数体里不许出现任何校验规则或排版规则。这是"未来 FastAPI 是第二个使用者而库不用改"的前提。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_pipeline.py`：

```python
import sys
from pathlib import Path

import pytest
from PIL import Image

from homework_compass.errors import FontError, NeedsConfirmation
from homework_compass.models import SourceKind
from homework_compass.parsing.extract import StubExtractor
from homework_compass.pipeline import (
    correct, dismiss, load_hw, parse_homework, render, save_hw, text_from_image,
)

pytestmark = pytest.mark.skipif(sys.platform != "darwin",
                                reason="候选表是 macOS 系统字体路径")

RAW = "1.数学：完成练习册P12-13，家长签字\n2.明天带美术材料：彩泥"
GOOD = {"items": [{"subject": "数学", "task": "完成练习册", "quantity": "P12-13",
                   "requirements": ["家长签字"]},
                  {"subject": "", "task": "明天带美术材料", "quantity": "",
                   "requirements": ["彩泥"]}],
        "extras": [], "unresolved": []}
# 单项用的 raw/stub：stub 说的每个字都得出自 raw，否则校验层会（正确地）判杜撰
ONE_RAW = "1.数学：练习册P12-13"
ONE = {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
       "extras": [], "unresolved": []}
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
LONG = "抄写本课生字每个两遍并注音" * 12


def test_parse_uses_injected_extractor():
    hw = parse_homework(RAW, extractor=StubExtractor(GOOD), name="小宇",
                        date="2026-11-06")
    assert len(hw.items) == 2 and hw.pending == []
    assert hw.student_name == "小宇" and hw.date == "2026-11-06"


def test_default_extractor_is_offline_not_paid():
    """库的默认路径不许花钱、不许联网。在线是调用方显式注入的事。"""
    hw = parse_homework("1.数学：练习册P12-13")
    assert len(hw.items) == 1


def test_render_refuses_when_pending_blocked(tmp_path):
    hw = parse_homework(RAW, extractor=StubExtractor({"items": [
        {"subject": "数学", "task": "完成练习册", "quantity": "P12-13"}],
        "extras": [], "unresolved": []}))
    assert hw.pending
    with pytest.raises(NeedsConfirmation):
        render(hw, out_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []          # 拒绝就不许留半成品


def test_render_writes_a4_300dpi_png(tmp_path):
    hw = parse_homework(RAW, extractor=StubExtractor(GOOD))
    r = render(hw, out_dir=tmp_path)
    assert (r.width, r.height) == (2480, 3508) and r.dpi == (300, 300)
    with Image.open(r.path) as im:
        assert im.size == (2480, 3508)
    assert r.used_placeholder is True               # 没传 --base 就是预览件
    assert r.issues == []


def test_render_with_real_base_is_not_placeholder(tmp_path):
    bp = tmp_path / "base.png"
    Image.new("RGB", (1240, 1754), "#EEF").save(bp)
    hw = parse_homework(RAW, extractor=StubExtractor(GOOD))
    r = render(hw, base=bp, out_dir=tmp_path)
    assert r.used_placeholder is False


def test_render_problems_are_carried_not_swallowed(tmp_path):
    """版面问题进 RenderResult.issues，不是吞掉，也不是拒绝出图。

    raw 里必须真的含这段长文：unsourced 的项会被降级成 pending，
    那样 render 会先按闸门拒绝，测不到 issues。
    """
    hw = parse_homework(LONG, extractor=StubExtractor({"items": [
        {"subject": "", "task": LONG, "quantity": ""}],
        "extras": [], "unresolved": []}))
    assert hw.pending == []
    r = render(hw, out_dir=tmp_path)
    assert r.issues


def test_roundtrip_through_json(tmp_path):
    hw = parse_homework(RAW, extractor=StubExtractor(GOOD))
    p = save_hw(hw, tmp_path / "hw.json")
    back = load_hw(p)
    assert [i.task for i in back.items] == [i.task for i in hw.items]
    assert back.source_text == hw.source_text


def test_correct_and_dismiss_go_through_the_parsing_layers_rules():
    """pipeline 只转发，不另立一套销账规则：补字段和按 id 销账都要真的生效。"""
    hw = parse_homework(RAW, extractor=StubExtractor({"items": [
        {"subject": "数学", "task": "完成练习册", "quantity": "P12-13"},
        {"subject": "", "task": "明天带美术材料", "quantity": ""}],
        "extras": [], "unresolved": []}))
    assert {p.text for p in hw.pending} == {"家长签字", "彩泥"}

    cleared = correct(hw, 1, "requirements", "家长签字，彩泥")
    assert cleared.pending == []           # 承接上了就销账
    assert hw.pending                      # 入参不被就地改写

    one = dismiss(hw, hw.pending[0].id)
    assert len(one.pending) == len(hw.pending) - 1
    assert any("家长确认不纳入" in n for n in one.report.notes)


def test_text_from_image_returns_ocr_kind(monkeypatch):
    from homework_compass import pipeline
    monkeypatch.setattr(pipeline, "ocr_to_text", lambda p, **kw: "1.数学练习册")
    text, kind = pipeline.text_from_image(Path("x.jpg"))
    assert kind is SourceKind.OCR and text == "1.数学练习册"


def test_configured_font_candidates_are_used(tmp_path):
    """spec §6.4「候选表可被配置覆盖」：配置里给的字体要真的被拿去解析。"""
    hw = parse_homework(ONE_RAW, extractor=StubExtractor(ONE))
    with pytest.raises(FontError, match="字形覆盖"):
        render(hw, out_dir=tmp_path, fonts=[ARIAL])
    r = render(hw, out_dir=tmp_path, fonts=[ARIAL, CJK])
    assert r.path.is_file()


def test_output_name_cannot_escape_out_dir(tmp_path):
    """date 可能来自模型或 --date，含 `../` 时不能把文件写到 out_dir 之外。"""
    hw = parse_homework(ONE_RAW, extractor=StubExtractor(ONE),
                        date="../../etc/2026-11-06")
    r = render(hw, out_dir=tmp_path)
    assert r.path.parent == tmp_path
    assert ".." not in r.path.name and "/" not in r.path.name


def _sources(sub: str | None = None) -> dict[str, str]:
    root = Path(__file__).resolve().parents[2] / "src" / "homework_compass"
    files = (root / sub).rglob("*.py") if sub else root.rglob("*.py")
    return {str(f.relative_to(root)): f.read_text(encoding="utf-8") for f in files}


def test_layout_never_imports_parsing():
    """spec §2 的依赖方向不是文档愿望：排版与校验必须各自能被单独测试复用。

    只查 `homework_compass.parsing` 这个导入路径，不查裸词 “parsing”：
    后者会被一句提到 `parse_homework` 的注释误伤，假阳性的拦截测试没人愿意维护。"""
    for name, text in _sources("layout").items():
        assert "homework_compass.parsing" not in text, name


def test_parsing_never_imports_layout():
    for name, text in _sources("parsing").items():
        assert "homework_compass.layout" not in text, name


def test_only_confirm_module_reads_the_terminal():
    """「库不做任何 IO 交互」必须能被机器检查，否则下一个 PR 就能塞进去一个 input()。"""
    for name, text in _sources().items():
        if name.startswith("cli/confirm.py"):
            continue
        assert "sys.stdin" not in text, name
        assert "input(" not in text, name
```

- [ ] **Step 2: 实现 pipeline.py**

```python
"""对外 API：四个动词——parse_homework / correct / dismiss / render。

本模块只编排，不含规则：一条校验判据、一处落位计算都不许写在这里，
否则「库的第一个使用者是 CLI、第二个是 Web」就变成一句空话。

降级路径（不花钱、不联网）是默认路径：extractor 不传就用 NaiveExtractor。
想调真实模型的使用方必须显式注入 LlmExtractor —— 让花钱成为显式决定。
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from PIL import Image

from homework_compass.errors import NeedsConfirmation
from homework_compass.layout import compose as compose_mod
from homework_compass.layout.skeleton import A4_DPI, get_skeleton
from homework_compass.models import (
    ParsedHomework, RenderResult, SourceKind, from_json, to_json,
)
from homework_compass.parsing.extract import (
    DEFAULT_OCR_MODEL, Extractor, NaiveExtractor, ocr_to_text,
)
from homework_compass.parsing.validate import (
    correct as _correct,
    dismiss as _dismiss,
    validate,
)

__all__ = ["parse_homework", "correct", "dismiss", "render", "save_hw", "load_hw",
           "text_from_image"]


def parse_homework(raw_text: str, *, extractor: Extractor | None = None,
                   date: str = "", name: str = "",
                   source_kind: SourceKind = SourceKind.TEXT) -> ParsedHomework:
    ex = extractor or NaiveExtractor()
    return validate(raw_text, ex(raw_text, date=date, name=name),
                    date=date, name=name, source_kind=source_kind)


def correct(hw: ParsedHomework, seq: int, field: str, value: str) -> ParsedHomework:
    return _correct(hw, seq, field, value)


def dismiss(hw: ParsedHomework, pending_id: str) -> ParsedHomework:
    return _dismiss(hw, pending_id)


def text_from_image(image: Path, *, model: str | None = None) -> tuple[str, SourceKind]:
    """照片 -> 文本。返回 kind 是为了让调用方明白：这条路必须过家长确认。

    `ocr_to_text` 在模块顶层 import（不是函数体内），否则它不可被测试替换。
    """
    return ocr_to_text(image, model=model or DEFAULT_OCR_MODEL), SourceKind.OCR


def render(hw: ParsedHomework, *, skeleton: str = "quest-map", skin: str = "dinosaur",
           base: Path | None = None, out_dir: Path = Path("out"),
           panel_alpha: int = 190,
           fonts: Sequence[str] | None = None) -> RenderResult:
    """pending 非空就拒绝出图（spec §5.3 的闸门），版面问题则如实带进 issues。"""
    if hw.pending:
        raise NeedsConfirmation(
            "存在待家长确认项，按「宁缺毋编」拒绝出图：\n"
            + "\n".join(f"  - [{p.reason.value}] {p.text}" for p in hw.pending))
    skel = get_skeleton(skeleton)
    base_image = None
    if base is not None:
        with Image.open(base) as im:      # 句柄不挂到出图之后：Windows 上会锁文件
            base_image = im.copy()
    img, issues = compose_mod.compose(hw, skel, skin=skin, base=base_image,
                                      panel_alpha=panel_alpha, fonts=fonts)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"homework_{_slug(hw.date)}_{_slug(skeleton)}_{_slug(skin)}.png"
    img.save(path, format="PNG", dpi=(A4_DPI, A4_DPI))
    return RenderResult(path=path, width=img.size[0], height=img.size[1],
                        dpi=(A4_DPI, A4_DPI), issues=issues,
                        used_placeholder=base is None)


def _slug(text: str) -> str:
    """文件名只留安全字符：date 可能来自模型或 `--date`，含 `/` 或 `..` 会写到 out_dir 之外。"""
    safe = re.sub(r"[^\w-]+", "-", str(text or "")).strip("-")
    return safe or "undated"


def save_hw(hw: ParsedHomework, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_json(hw), ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path


def load_hw(path: Path) -> ParsedHomework:
    return from_json(json.loads(Path(path).read_text(encoding="utf-8")))
```

三处与初稿不同，都是测试与实跑逼出来的：

- `base` 的句柄：初稿 `Image.open(base)` 永不关闭，Windows 上出图后原图被锁；改成 `with` + `copy()`。
- `_slug`：初稿直接拼 `hw.date`。date 可以来自模型或 `--date`，`../../etc` 就能把图写到 `out_dir` 之外；现在非安全字符一律转 `-`。
- stub 与 raw 必须对得上：初稿的 6 个测试用 `StubExtractor(GOOD)` 去解析 `"1.数学：练习册P12-13"`，而 GOOD 声称的第二项（`明天带美术材料`/`彩泥`）在原文里根本不存在。这不是实现有 bug：校验层把它们判成 fabricated、闸门拒绝出图，正是「零杜撰」在生效。修的是测试——每个 stub 只许说 raw 里有的字；单项场景另用 `ONE_RAW`/`ONE`。

`__init__.py` 填导出（只导 public 动词与类型，内部模块不对外）：

```python
"""每日作业目标生成器核心包。

库只返回结构，不做任何终端交互（CLI 在 `homework_compass.cli`）。
对外只暴露 `pipeline` 的动词、数据模型与异常层级；内部模块（parsing / layout /
config / llm_client）是实现细节，不进 `__all__`。
"""

from homework_compass.errors import (
    ApiError, ConfigError, ExtractionError, FontError, HomeworkError, LayoutError,
    NeedsConfirmation,
)
from homework_compass.models import (
    HomeworkItem, ParsedHomework, PendingItem, RenderResult,
)
from homework_compass.pipeline import (
    correct, dismiss, load_hw, parse_homework, render, save_hw, text_from_image,
)

__all__ = ["parse_homework", "correct", "dismiss", "render", "save_hw", "load_hw",
           "text_from_image", "ParsedHomework", "HomeworkItem", "PendingItem",
           "RenderResult", "HomeworkError", "ExtractionError", "NeedsConfirmation",
           "LayoutError", "FontError", "ApiError", "ConfigError"]
```

- [ ] **Step 3: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_pipeline.py -q`
Expected: `14 passed`（全量 `174 passed, 1 deselected`；poc 仍 `44 passed`）

- [ ] **Step 4: Commit**

```bash
git add src/homework_compass/pipeline.py src/homework_compass/__init__.py tests/unit/test_pipeline.py
git commit -m "feat: 对外 API 编排层（pending 非空拒绝出图，默认路径不花钱）"
```

---

## Task 16: CLI 子命令与退出码

**Files:**
- Create: `src/homework_compass/cli/__init__.py`
- Create: `src/homework_compass/cli/main.py`
- Create: `tests/unit/test_cli.py`
- Create: `README.md`

**Interfaces:**
- Consumes: `pipeline.*`、`config.load_config / load_dotenv_default`、`layout.skeleton.zones_report / build_prompt / get_skeleton`、`errors.*`
- Produces:

```python
EXIT_OK = 0 ; EXIT_PENDING = 2 ; EXIT_PARSE_PENDING = 3 ; EXIT_USAGE = 4 ; EXIT_REMOTE = 5
def build_parser() -> argparse.ArgumentParser
def main(argv: list[str] | None = None) -> int
```

退出码是对外契约（脚本与 AI 助手都靠它分支），一经确定不得改：`0 成功 / 2 有 pending 拒绝出图 / 3 解析产生 pending / 4 参数或白名单错误 / 5 API 或字体错误`。

- [ ] **Step 1: 写失败测试（用 tmp_path 与 `--offline`，零网络）**

```python
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
    `--resolve` 根本无法从命令行抵达。手工造一份带 pending 的 hw.json 才能构造出它。"""
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
    assert main(["render", str(hw), "--skeleton", "nope", "--out", str(tmp_path)]) == EXIT_USAGE


def test_bad_flag_exits_four_not_two():
    """命令行写错绝不能返回 2。2 的含义是「有 pending，要家长看」，
    而 argparse 出错时默认 `sys.exit(2)`，会让调用方把拼错参数当成一次正常拒绘。

    三个 case 各挡一条路（均已在 Python 3.13 上实测）：子命令内部的坏旗、
    未知子命令、缺必填位置参数——后两类走的是父 parser 的 error()，
    只修子 parser 拦不住。（坏旗 `--nope` 会被 argparse 先当成缺少 `hw` 位置参数，
    两者都该映射到 4，所以不断言具体报错文本。）"""
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
```

- [ ] **Step 2: 实现 main.py**

```python
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
                 if rn and (rn in norm(p.text) or (p.source_sentence and rn in norm(p.source_sentence)))]
        if len(cands) != 1:
            raise ValueError(f"无法定位待确认项「{ref}」（匹配 {len(cands)} 条，请用 id）")
        target = cands[0]
    return pipeline.dismiss(hw, target.id)


def _render(args, cfg) -> int:
    if not args.hw.is_file():
        # 不先查就 read_text：FileNotFoundError/OSError 不在下面的 except 里，
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
```

`cli/__init__.py` 必须**只写 docstring**：不 re-export 任何名字。测试用
`from homework_compass.cli import main as cli_main` 拿模块本身去替身
`LlmExtractor`；一旦这里写 `from ... import main`，拿到的就是函数，替身失效。

```python
"""CLI 适配层。本包只有两个模块：

- `main`：参数解析、退出码翻译、把结果读给人看；
- `confirm`：唯一的终端交互（`hw confirm`），其余模块一律不碰 stdin。

`__init__` 故意不 re-export 任何名字：`from homework_compass.cli import main`
必须拿到 `main` 模块本身（测试要在它的命名空间里替身 `LlmExtractor`），
一旦这里写 `from ... import main`，拿到的就是函数，替身会静默失效。
"""
```

五处与初稿不同，都有测试撑腰：

- `fonts=cfg.fonts`：不加就是 T14 的“死配置”，spec §6.4.1 的候选表永远到不了 `render`。
- `--text-model` / `--ocr-model`：初稿 `--text-model` 根本没被使用，而 `--image` 的 OCR 又去拿了 text 模型。现在两条链路各自覆盖各自的配置项。
- `ExtractionError → 5`：模型返回的不是对象，这是上游坏了（spec §8.3 的“API 错误”），不是用户参数写错；映射成 4 会让脚本白白重放一次可能计费的请求。
- `render` 先查 `hw` 文件存在：裸 `FileNotFoundError` 不在 except 里，会变成 `exit 1 + traceback`，破坏退出码契约。真进程探针当场抓到过。
- `test_parse_exit_code_matches_pending_state` 换成 OCR 路径：离线解析器从不让 pending 非空（探针确认），原测试永远只走 `EXIT_OK` 分支，是条空转断言。现在用 `--image` + 替身 OCR 真正触发 `EXIT_PARSE_PENDING`，并锁住「hw.json 仍落盘」与「OCR 走 `cfg.ocr_model`」。

`README.md` 写三件事就够（安装、三条命令、退出码表）：

```markdown
# HomeworkCompass

老师发的任意格式作业 → 机械校验 → A4 300dpi 目标图。零杜撰、零遗漏、有歧义必拦。

    python3 -m pip install -e ".[dev]"

    hw parse --file raw.txt --name 小宇 --offline --out hw.json
    hw confirm hw.json
    hw render hw.json --out out/

- `parse` 把原文拆成结构化作业，任何没出处、没覆盖的片段都进 `pending`；
- `confirm` 逐条过 `pending`（只在 tty 上交互）；
- `render` 出 A4 2480×3508 @300dpi PNG。`pending` 非空时拒绝出图，一个字节都不写。

不传 `--base` 时用占位底图，只用于核对对位，不是可打印成品。

`DASHSCOPE_API_KEY` 只从环境变量读取，配置里没有这个字段。不写 `--offline` 才会调用在线模型。

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 2 | 存在 pending，拒绝出图 |
| 3 | 解析产生了 pending |
| 4 | 参数或字段白名单错误 |
| 5 | API 或字体错误 |

坐标契约与生图提示词也能单独打印（不花钱）：

    hw zones
    hw prompt --skeleton quest-map --skin dinosaur
```

- [ ] **Step 3: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_cli.py -q`
Expected: `16 passed`（全量 `190 passed, 1 deselected`；poc 仍 `44 passed`）

手动验收（真进程，退出码落在外壳里）：

```bash
hw parse --file raw.txt --name 小宇 --offline --out hw.json   # 0
hw render hw.json --out out/                                   # 0，2480x3508
hw render                                                      # 4（argparse 缺参数）
hw render --skeleton nope hw.json                              # 4
hw render nonexist.json                                        # 4（文件不存在）
```

- [ ] **Step 4: Commit**

```bash
git add src/homework_compass/cli/__init__.py src/homework_compass/cli/main.py tests/unit/test_cli.py README.md
git commit -m "feat: hw 子命令与退出码契约（parse/confirm/render/zones/prompt）"
```

---

## Task 17: 交互式销账（全项目唯一碰 tty 的模块）

**Files:**
- Create: `src/homework_compass/cli/confirm.py`
- Create: `tests/unit/test_confirm_cli.py`

**Interfaces:**
- Consumes: `pipeline.correct / dismiss / load_hw / save_hw`、`models.PendingReason`
- Produces: `def run_confirm(hw_path: Path, *, stdin=None, stdout=None) -> int`

库不做 IO，交互只在这里。**非 tty 必须拒绝交互**：输出结构化 JSON + 退出码 3。这样它既能被 AI 助手对话直接调用（上游文档阶段 1 形态），也能被未来的 Web 端复用同一套 pending 结构。

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 实现 confirm.py**

```python
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
```

两条硬约束：销账只能走 `pipeline.dismiss()`，本文件里不得出现自己过滤 `hw.pending` 的代码；`_ask()` 不得出现任何“这条该不该上图”的判断。

**六处与初稿不同（都是先探针、后定稿）**：

1. 初稿的 `pending_hw`（`RAW` + 只认领数学一行的 stub）实测吃出 **2 条** pending（`明天带美术材料`、`彩泥`），且两条 `related_seq` 都是 `None`；「(d) 一次就清空」和「关联：第 N 项」两个断言都立不住。改用 `RAW_ONE = "1.数学：完成练习册P12-13，家长签字"`：恰好 1 条 `家长签字`、`related_seq=1`、`source_sentence` 非空。两条 pending 的场景留给 `RAW_TWO`，专走「先问第几项」的分支。
2. `cf.pipeline._real_correct` 不存在。测试在 monkeypatch 之前先抓 `real = cf.pipeline.correct`，替身再转发给它。
3. 初稿没考虑「编辑已经把这条 pending 覆盖掉、随后的 dismiss id 已失效」：`pipeline.dismiss()` 对不存在的 id 会抛 `ValueError`，到用户手里就是崩。`run_confirm` 在 dismiss 前先确认 id 还在 `pending` 里——销账仍然只走 `dismiss()`，只是不把「已经解决」当错误。
4. `hw confirm nope.json` 会裸抛 `FileNotFoundError`，穿出 `main()` 变成 exit 1，破坏退出码契约。和 Task 16 的 `_render` 一样，先 `is_file()` 检查 → 4。
5. 三处健壮性收口：`REASON_CN.get(p.reason, p.reason.value)`（未知 reason 不再 `KeyError`）；`e` 路径的字段名先过 `EDITABLE_FIELDS` 白名单（与 `hw parse --set` 同一集合，来自 `parsing.validate`）；EOF 落在序号提示上时打印「没有有效序号，跳过。」而不是空转。
6. 初稿 7 个测试，实际 12 个：补了「先问第几项」「序号处 EOF」「乱输入重问」「编辑后 dismiss 已失效」「文件不存在」「prompt 里真的印出关联序号」。

- [ ] **Step 3: 跑测试确认通过**

Run: `python3 -m pytest tests/unit/test_confirm_cli.py -q`
Expected: `12 passed`

- [ ] **Step 4: 全量单测**

Run: `python3 -m pytest -q`
Expected: 全部通过，且无网络请求（`-m 'not network'` 生效）。实测 `202 passed, 1 deselected`。

- [ ] **Step 5: Commit**

```bash
git add src/homework_compass/cli/confirm.py tests/unit/test_confirm_cli.py
git commit -m "feat: 交互式销账（非 tty 拒绝交互，输出结构化 JSON + 退出码 3）"
```

---

## Task 18: 集成 · 回归 · 平价校验 · 删除 poc

**Files:**
- Create: `tests/fixtures/raw1.txt`
- Create: `tests/fixtures/raw2.txt`
- Create: `tests/integration/test_full_pipeline.py`
- Create: `tests/regression/test_poc_bugs.py`
- Create: `parity_check.py`（一次性脚本，平价通过后**删除**）
- Delete: `poc/`

**Interfaces:**
- Consumes: 前面所有任务
- Produces: DoD 证据

- [ ] **Step 1: 落地两份真实原文（逐字，不要重新构造）**

内容取自 poc 实跑保存的 `source_text`（本地文件 `poc/out/hw_raw1.json` / `hw_raw2.json`）。**注意**：`poc/out/` 被 `.gitignore` 排除，所以这两个 fixture 必须作为新库的正式文件提交，不能依赖 poc 产物——spec §10 那句"直接从 poc/out 抽取"只对本地成立，不对仓库成立。

**实测校准**：① `poc/out/raw2.txt` 与 `hw_raw2.json` 的 `source_text` 都是 158 字，`④` 后**没有**空格；初稿转写多了一个空格（160 字），按「逐字」原则以真实产物为准。② `poc/out/raw1.txt` 与初稿逐字相同。两份 fixture 与 `poc/out/raw{1,2}.txt` 已用 `cmp` 校验一致。

`tests/fixtures/raw1.txt`（含行尾换行，逐字保留 emoji 与全角标点）：

```
📚今日作业：
1.数学：完成练习册 P12-13，用铅笔，家长检查后签字
2.语文：抄写本课生字 每个2遍，书写工整
3.英语：听读打卡 Unit 3，10分钟，APP打卡
4.明天带美术材料：彩泥
温馨提示：请今晚完成
```

`tests/fixtures/raw2.txt`：

```
各位家长好！今天（11月5日）的作业如下：
①语文：《静夜思》背诵并默写，家长签字
②数学：练习册第12-13页，完成后校对答案
③英语：跟读Unit3 A部分单词，APP打卡
④科学：观察植物的变化，写一篇观察日记（下周三交）
⑤美术：准备好彩泥和剪刀
另外 明天记得穿校服，书包里放好水彩笔。
收到请回复，谢谢！
```

- [ ] **Step 2: 写集成测试（StubExtractor，零网络）**

`tests/integration/test_full_pipeline.py`：

```python
"""全链路集成：两份真实原文 → 提取 → 校验 → 落盘 → 出图，默认零网络。"""

import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from homework_compass.cli.confirm import run_confirm
from homework_compass.cli.main import (
    EXIT_OK, EXIT_PARSE_PENDING, EXIT_PENDING, main,
)
from homework_compass.errors import NeedsConfirmation
from homework_compass.models import SourceKind
from homework_compass.parsing.extract import NaiveExtractor, StubExtractor
from homework_compass.pipeline import load_hw, parse_homework, render, save_hw

FIX = Path(__file__).resolve().parents[1] / "fixtures"
needs_macos_fonts = pytest.mark.skipif(sys.platform != "darwin",
                                       reason="出图需要本机 CJK 字体")

# 每份 payload 只声称对应原文里有的字：stub 一旦越界，校验层会按「零杜撰」
# 把它降级成 pending——那是另一条测试要测的东西，不是这里。
FOUR = {"items": [
    {"subject": "数学", "task": "完成练习册 P12-13", "quantity": "",
     "requirements": ["用铅笔", "家长检查后签字"]},
    {"subject": "语文", "task": "抄写本课生字", "quantity": "每个2遍",
     "requirements": ["书写工整"]},
    {"subject": "英语", "task": "听读打卡 Unit 3", "quantity": "10分钟",
     "requirements": ["APP打卡"]},
    {"subject": "美术", "task": "明天带美术材料：彩泥", "quantity": ""}],
    "extras": ["温馨提示：请今晚完成"], "unresolved": []}

FIVE = {"items": [
    {"subject": "语文", "task": "《静夜思》背诵并默写", "quantity": "",
     "requirements": ["家长签字"]},
    {"subject": "数学", "task": "练习册", "quantity": "第12-13页",
     "requirements": ["完成后校对答案"]},
    {"subject": "英语", "task": "跟读Unit3 A部分单词", "quantity": "",
     "requirements": ["APP打卡"]},
    {"subject": "科学", "task": "观察植物的变化，写一篇观察日记", "quantity": "",
     "requirements": ["下周三交"]},
    {"subject": "美术", "task": "准备好彩泥和剪刀", "quantity": ""}],
    "extras": ["明天记得穿校服", "书包里放好水彩笔"], "unresolved": []}

PAIRS = (("raw1.txt", FOUR), ("raw2.txt", FIVE))

RAW_ONE = "1.数学：完成练习册P12-13，家长签字"
ONE = {"items": [{"subject": "数学", "task": "完成练习册", "quantity": "P12-13"}],
       "extras": [], "unresolved": []}


def raw(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


@needs_macos_fonts
def test_parse_to_png_for_both_real_samples(tmp_path):
    for name, payload in PAIRS:
        hw = parse_homework(raw(name), extractor=StubExtractor(payload),
                            name="小宇", date="2026-11-06")
        assert hw.pending == [], (name, [p.text for p in hw.pending])
        r = render(hw, out_dir=tmp_path / name)
        assert (r.width, r.height, r.dpi) == (2480, 3508, (300, 300))
        with Image.open(r.path) as im:
            assert im.size == (2480, 3508)


def test_four_elements_present_on_every_item():
    """DoD §11.3 的机器部分：科目/内容必有；数量与要求至少有一类落在卡面；
       高优项必须带得出信号（星标与「重要」由排版层据此标注）。"""
    hw = parse_homework(raw("raw2.txt"), extractor=StubExtractor(FIVE))
    assert len(hw.items) == 5
    for it in hw.items:
        assert it.subject and it.task
        assert it.seq > 0
        assert it.priority in ("high", "normal")
    assert any(i.quantity for i in hw.items)
    assert sum(1 for i in hw.items if i.requirements_all) >= 3
    high = [i for i in hw.items if i.priority == "high"]
    assert high and all(i.priority_signals for i in high)
    assert hw.extras                                    # 底部「别忘了」条有内容


def test_fabricated_field_never_reaches_the_card(tmp_path):
    """DoD §11.5：注入原文没有的「用铅笔」。"""
    invented = {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13",
                           "requirements": ["用铅笔"]}], "extras": [], "unresolved": []}
    hw = parse_homework("1.数学：练习册P12-13", extractor=StubExtractor(invented))
    assert hw.items[0].requirements == []
    assert [p.text for p in hw.pending] == ["用铅笔"]
    with pytest.raises(NeedsConfirmation) as ei:
        render(hw, out_dir=tmp_path)
    assert "用铅笔" in str(ei.value)
    assert list(tmp_path.rglob("*.png")) == []


def test_omitted_item_becomes_pending():
    """DoD §11.6：原文 5 项只抽 4 项。"""
    payload = json.loads(json.dumps(FIVE))
    payload["items"] = payload["items"][:1] + payload["items"][2:]     # 漏掉数学
    hw = parse_homework(raw("raw2.txt"), extractor=StubExtractor(payload))
    texts = [p.text for p in hw.pending]
    assert any("第12-13页" in t for t in texts)
    assert any("校对答案" in t for t in texts)


def test_pending_blocks_render(tmp_path):
    hw = parse_homework(RAW_ONE, extractor=StubExtractor(ONE))
    assert [p.text for p in hw.pending] == ["家长签字"]
    with pytest.raises(NeedsConfirmation):
        render(hw, out_dir=tmp_path)
    assert list(tmp_path.rglob("*.png")) == []


@needs_macos_fonts
def test_confirm_loop_then_render_opens_the_gate(tmp_path):
    """parse → confirm → render 全链，顺带把退出码 3/2/0 各走一遍。"""
    hw = parse_homework(RAW_ONE, extractor=StubExtractor(ONE), date="2026-11-06")
    p = save_hw(hw, tmp_path / "hw.json")
    out = tmp_path / "out"

    assert main(["render", str(p), "--out", str(out)]) == EXIT_PENDING
    before = p.read_text(encoding="utf-8")
    assert run_confirm(p, stdin=io.StringIO("")) == EXIT_PARSE_PENDING   # 非 tty 不写盘
    assert p.read_text(encoding="utf-8") == before

    tty = io.StringIO("e\nrequirements\n家长签字\n")
    tty.isatty = lambda: True                # type: ignore[assignment]
    assert run_confirm(p, stdin=tty) == EXIT_OK
    assert load_hw(p).pending == []

    assert main(["render", str(p), "--out", str(out)]) == EXIT_OK
    assert len(list(out.glob("*.png"))) == 1


def test_offline_path_on_real_samples_produces_no_pending():
    expected = {"raw1.txt": 5, "raw2.txt": 6}
    for name, count in expected.items():
        hw = parse_homework(raw(name), extractor=NaiveExtractor(), date="2026-11-06")
        assert len(hw.items) == count, name
        assert hw.pending == [], (name, [p.text for p in hw.pending])


def test_json_is_the_only_hub_between_commands(tmp_path):
    hw = parse_homework(raw("raw2.txt"), extractor=StubExtractor(FIVE),
                        date="2026-11-06")
    p = save_hw(hw, tmp_path / "hw.json")
    back = load_hw(p)
    assert [i.task for i in back.items] == [i.task for i in hw.items]
    assert back.source_text == hw.source_text        # 重跑校验要靠它
    assert back.source_kind is SourceKind.TEXT
```

**四处与初稿不同（都是探针先行的结果）**：

1. 初稿对两份原文共用同一个 `FIVE`：在 raw1 上实测吃出 **22 条** pending——stub 声称的《静夜思》《彩泥》等根本不在 raw1 里，校验层按「零杜撰」全部降级。改为 `FOUR` / `FIVE` 一一对齐（`PAIRS`），且 `FIVE` 的科学项 task 补上原文里的「观察植物的变化」，否则 raw2 会剩 1 条 `uncovered`。
2. `test_four_elements_present_on_every_item` 断言 `it.task` 非空太弱：美术项既无 quantity 也无 requirements，单看字段会误判。改成「科目/任务必有 + 至少一项有数量 + 至少三项有要求 + 高优项必须带 `priority_signals`」。
3. `pytest.raises(Exception)` 看不出闸门语义，且 `render` 的报错文案不含「宁缺毋编」（那是 CLI 的措辞）。改为 `NeedsConfirmation`，并把断言换成 pending 文本出现在异常里。
4. 初稿的 confirm 测试只用库函数 `dismiss`，没走 CLI。改成真实链路：`main render` 2 → 非 tty `run_confirm` 3（且文件字节不变）→ tty 里 `e` 补齐 → `run_confirm` 0 → `main render` 0 并出一张 PNG；退出码 3/2/0 各断言一次。

- [ ] **Step 3: 写回归测试（注释必须写明"曾经怎么坏"）**

`tests/regression/test_poc_bugs.py`（实际 7 条：四个 bug 类，其中套话过滤与销账死胡同各拆成双向断言）：

```python
"""poc 期间四个真实 bug，每个一条具名测试。它们的共同点：都不报错。"""

import re

from homework_compass.models import PendingReason, SourceKind
from homework_compass.parsing.extract import StubExtractor
from homework_compass.parsing.validate import claimed_text, is_covered, validate
from homework_compass.pipeline import correct, dismiss, parse_homework, render

RAW_ONE = "1.数学：完成练习册P12-13，家长签字"
ONE = {"items": [{"subject": "数学", "task": "完成练习册", "quantity": "P12-13"}],
       "extras": [], "unresolved": []}


def test_confirmation_loop_is_not_a_dead_end(tmp_path):
    """曾经：poc 初版 `--set` 改完字段，unresolved 永远清不掉，
       确认环节能进不能出，图永远生不成（实测 EXIT=3 卡死）。"""
    hw = parse_homework(RAW_ONE, extractor=StubExtractor(ONE))
    assert [p.text for p in hw.pending] == ["家长签字"]
    after = correct(hw, 1, "requirements", "家长签字")
    assert after.pending == []
    render(after, out_dir=tmp_path)                  # 现在画得出来了


def test_boilerplate_never_reaches_parent():
    """曾经：模型把「各位家长好！今天作业如下：」原样塞进 unresolved，
       poc 透传给家长，一次跑出 8 条假待确认项——产品直接没法用。"""
    raw = ("各位家长好！今天（11月5日）的作业如下：\n1.数学练习册P12-13\n收到请回复，谢谢！")
    hw = validate(raw, {"items": [{"subject": "数学", "task": "练习册",
                                   "quantity": "P12-13"}],
                        "extras": [],
                        "unresolved": ["各位家长好", "今天作业如下", "收到请回复", "谢谢"]})
    assert hw.pending == []
    assert hw.report.stats["auto_dropped_boilerplate"] >= 3


def _norm(text: str) -> str:
    """去掉标点与空白：原文在「：」处会被拆成两条 pending，拼起来才是原句。"""
    return re.sub(r"[\W_]", "", text)


def test_real_homework_never_auto_dropped():
    """套话过滤的危险方向：把真作业当客话吞掉。这条测试存在的意义就是
       防止上条测试被「优化」成一律丢弃。"""
    real = ["明天带美术材料：彩泥", "今晚十点前完成", "后天交观察日记",
            "周一带上跳绳", "收到书本后签字"]
    for line in real:
        hw = validate(f"1.数学练习册P12-13；{line}", {"items": [
            {"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
            "extras": [], "unresolved": []})
        surfaced = _norm("".join(p.text for p in hw.pending))
        assert _norm(line) in surfaced, line


def test_requirement_not_printed_twice():
    """曾经：渲染出的 A4 上「家长签字/APP打卡/校对答案/下周三交」各印两遍——
       模型把整句当 task、又把句尾要求单列一份，两边都上图。"""
    text = "1.数学：完成练习册P12-13，家长签字"
    hw = validate(text, {"items": [{"subject": "数学", "task": "完成练习册P12-13，家长签字",
                                    "quantity": "", "requirements": ["家长签字"]}],
                         "extras": [], "unresolved": []})
    it = hw.items[0]
    assert it.requirements == []                       # 显示层不重复
    assert it.requirements_all == ["家长签字"]         # 判定层仍生效
    assert it.priority == "high"


def test_pending_does_not_cover_itself():
    """曾经：claimed_text() 把 unresolved 也算进「已认领」，
       于是每条待确认项自己认领自己，一条都销不掉。"""
    hw = validate(RAW_ONE, ONE)
    p = hw.pending[0]
    assert p.text in claimed_text(hw, include_pending=True)
    assert not is_covered(p.text, hw)


def test_ocr_notice_can_be_cleared():
    """曾经：OCR 强制确认项在销账**之后**才追加，于是它永远清不掉（同类死胡同）。"""
    hw = validate("1.数学练习册P12-13", {"items": [{"subject": "数学", "task": "练习册",
                                                    "quantity": "P12-13"}],
                                         "extras": [], "unresolved": []},
                  source_kind=SourceKind.OCR)
    pid = next(p.id for p in hw.pending if p.reason is PendingReason.OCR_UNVERIFIED)
    assert dismiss(hw, pid).pending == []


def test_connector_prefixed_line_not_double_reported():
    """曾经：原文「另外明天记得穿校服」，extras 已有「明天记得穿校服」，
       不剥连接词就误报一条遗漏。"""
    hw = validate("1.数学练习册P12-13\n另外明天记得穿校服",
                  {"items": [{"subject": "数学", "task": "练习册", "quantity": "P12-13"}],
                   "extras": ["明天记得穿校服"], "unresolved": []})
    assert hw.pending == []
```

**三处与初稿不同**：① 初稿的销账回归用 `correct(hw, 1, "requirements", "明天带美术材料：彩泥")`：它虽然能清掉（整串都能在原文溯源），但把「明天带美术材料」当成了数学项的要求，正好是 T8「别改错项」要防的那类错。改用 `RAW_ONE` + `家长签字`，语义与真实操作一致。② `test_real_homework_never_auto_dropped` 的 `any(...) or hw.pending` 恒等于 `hw.pending`，且「明天带美术材料：彩泥」会被拆成两条 pending，`line in p.text` 永远不成立；改为把 pending 拼起来、去标点后断言包含。③ 初稿把 `correct`/`dismiss`/`claimed_text` 写在函数体里，统一提到顶层 import。

- [ ] **Step 4: 平价校验（一次性，`parity_check.py`）**

跑之前先确认 poc 还能跑（Task 1 已把 poc 入库，可回退比对）。`parity_check.py` 对两份原文分别跑 poc 与新包，打印四组数字并断言：items 数、pending 文本集合、priority 序列、成图尺寸与 DPI。

```python
"""一次性平价脚本：跑通即删，不进正式包。

对两份真实原文分别跑 poc（离线兜底）与新包，比对 items 数、pending、priority
与成图尺寸，并把每一处差异写成断言——差异只许出现在已声明清单里。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = Path(tempfile.mkdtemp(prefix="parity-"))
FIXTURES = ROOT / "tests" / "fixtures"


def norm(text: str) -> str:
    """去连接词、空白与标点：新包会剥掉「另外」与句末标点（已知差异 5），
    字面不能再直比。"""
    t = re.sub(r"^(另外|此外|还有|然后|接着|以及|并且|同时|其它|其他|补充|注意|提醒)",
               "", (text or "").strip())
    return re.sub(r"[\W_]", "", t)


def run_poc(raw: Path) -> dict:
    out = OUT / f"poc_{raw.stem}.json"
    subprocess.run([sys.executable, str(ROOT / "poc" / "parse_homework.py"),
                    "--file", str(raw), "--no-llm", "--out", str(out)], check=True,
                   capture_output=True)
    return json.loads(out.read_text(encoding="utf-8"))


def run_new(raw: Path) -> dict:
    sys.path.insert(0, str(ROOT / "src"))
    from homework_compass.parsing.extract import NaiveExtractor
    from homework_compass.pipeline import parse_homework
    hw = parse_homework(raw.read_text(encoding="utf-8"), extractor=NaiveExtractor(),
                        date="2026-11-06")
    return {"items": [{"subject": i.subject, "task": i.task, "quantity": i.quantity,
                       "priority": i.priority} for i in hw.items],
            "unresolved": [p.text for p in hw.pending]}


# 已知且**有意为之**的差异，不得为了让平价通过而回退校验规则：
#  1. 「准备」「重点」已从 PRIORITY_MARKERS 移除（spec §5.5 规则 2）
#     → raw2 的美术项 poc=high / 新包=normal。
#  2. 兜底解析器改按句切分（Task 9）→ raw2 poc 7 项（含垃圾标题项）/ 新包 6 项。
#     新包少的那一项是 poc 印上纸的「好！今天（11月5日）的作业如下：」，
#     差异方向是「去掉垃圾」，属于修好，不是丢掉作业。
#  3. pending 由裸字符串升级为 PendingItem（文本内容一致，结构不同）。
#  4. 周X 全周七天都是截止时间信号（spec §5.5 规则 2 的「周X」），
#     poc 的 HIGH_KEYWORDS 没有星期词 → raw2 的第 4 项（含「下周三交」）
#     poc=normal / 新包=high。差异方向是「多提醒一次」，不丢内容。
#  5. 连接词剥离与句末标点归一（Task 5）→ raw2 最后一项 poc 带「另外」「。」，
#     新包不带。字面不同、承载的内容相同，比较前统一 norm()。
DELTA_TASKS = {"raw1.txt": 5, "raw2.txt": 6}
DELTA_PRIORITIES = {"raw1.txt": ["high", "normal", "high", "high", "normal"],
                    "raw2.txt": ["high", "normal", "high", "high", "normal", "high"]}
# poc 独有、允许消失的项（只许是套话，不许是作业）
DROP_ALLOWED = {"raw1.txt": set(), "raw2.txt": {"好今天11月5日的作业如下"}}


def main() -> int:
    for name in ("raw1.txt", "raw2.txt"):
        a, b = run_poc(FIXTURES / name), run_new(FIXTURES / name)
        print(f"== {name} ==  poc {len(a['items'])} 项 / 新包 {len(b['items'])} 项")
        print("   poc pending:", a["unresolved"])
        print("   新包 pending:", b["unresolved"])
        assert len(b["items"]) == DELTA_TASKS[name], f"{name} 项数与预期平价差异不符"
        assert [i["priority"] for i in b["items"]] == DELTA_PRIORITIES[name], name
        assert a["unresolved"] == b["unresolved"] == [], name

        poc_tasks = {norm(i["task"]) for i in a["items"]}
        new_tasks = {norm(i["task"]) for i in b["items"]}
        extra = new_tasks - poc_tasks
        assert not extra, f"{name} 出现了 poc 没有的内容：{sorted(extra)}"
        dropped = poc_tasks - new_tasks
        assert dropped == DROP_ALLOWED[name], f"{name} 丢掉的不是声明过的套话：{sorted(dropped)}"

        # 成图尺寸与 DPI：新包出图必须仍是 A4 300dpi
        from homework_compass.parsing.extract import NaiveExtractor
        from homework_compass.pipeline import parse_homework, render
        hw = parse_homework((FIXTURES / name).read_text(encoding="utf-8"),
                            extractor=NaiveExtractor(), date="2026-11-06")
        r = render(hw, out_dir=OUT / name)
        assert (r.width, r.height, r.dpi) == (2480, 3508, (300, 300)), name
        print(f"   成图 {r.path.name} {r.width}x{r.height} dpi={r.dpi}")

    print("平价校验通过：除五处已声明差异外，行为一致。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**两处与初稿不同**：① 初稿的 `all(i["task"] in poc_tasks ...)` 在 raw2 上必失败：新包最后一项剥掉了「另外」与句末「。」，`in` 判假。改为 `norm()` 两侧归一（去连接词、标点、空白），并把「poc 独有项」限定到 `DROP_ALLOWED` 白名单（raw2 只允许垃圾标题消失）。② `run_poc` 用临时目录而不是 `poc/out`，脚本删了不留产物；成图尺寸/DPI 也在脚本里真跑一次 `render` 断言，而不是只看 JSON。

Run: `python3 parity_check.py`
Expected: `平价校验通过：除五处已声明差异外，行为一致。`

实测输出：raw1 poc 5 项 / 新包 5 项、pending 均空；raw2 poc 7 项 / 新包 6 项、pending 均空；两份成图均 2480x3508 dpi=(300,300)。

**如果断言失败**：先判断差异方向。"新包少了一项" 必须逐字确认少的是不是套话；"新包多报了 pending" 才是真的漂移。绝不允许把校验规则改回 poc 的样子来凑通过。

- [ ] **Step 5: 人工抽查成图（DoD §11.3）**

```bash
hw parse --file tests/fixtures/raw2.txt --name 小宇 --offline --date 2026-11-06 --out /tmp/hw.json
hw render /tmp/hw.json --out /tmp/hw_out/
ls -la /tmp/hw_out/
open /tmp/hw_out/homework_2026-11-06_quest-map_dinosaur.png
```

**初稿的 `python3 -m hw` 不存在**：入口点是 pyproject 的 console script `hw`（或 `python3 -m homework_compass.cli.main`）；文件名日期由 `--date` 决定，初稿没传 `--date` 却写死了 `2026-11-06`。

肉眼核对四项：每项四要素齐全、高优项有星标+"重要"、底部有"别忘了"条、每项有勾选框。**并确认占位底图的提示出现过**（没传 `--base` 时它必须大声提示"这是排版预览，不是可打印成品"）。

**实际抽查用的是富数据卡**：离线兜底解析器 quantity/requirements 恒空（遗留问题 2），四要素看不全。用 `FIVE` payload 生成 `hw_rich.json` 后 `hw render` 实测：5 项、语文/英语/科学带星标与「重要」、数学项显示「(第12-13页)」与「完成后校对答案」、底部「别忘了」两条、每项勾选框、占位底图提示正常；`used_placeholder=True` 且 `issues == []`。

- [ ] **Step 6: 凭证自查（DoD §11.8）**

```bash
git ls-files | grep -E '(^|/)\.env$' && echo "!!! 凭证已入库" || echo "OK: 无 .env 跟踪"
git log --all --diff-filter=A --name-only --pretty=format: | sort -u \
  | grep -E '(^|/)\.env$' && echo "!!! 历史有 .env" || echo "OK: 历史无 .env"
git grep -n "sk-[A-Za-z0-9]" -- '*.py' '*.toml' \
  | grep -vE "sk-(xxx|test|ws|from-file|real)|sk- 开头" || echo "OK: 源码无真实 key"
```

**初稿的两处会误报**：① `grep -i "\.env"` 会命中 `poc/.env.example`（历史提交里的示例文件，没有真 key）→ 必须锚定 basename 为 `.env`；② `sk-` 过滤只排除了 `sk-xxx|sk-test`，会漏网 `sk-from-file`/`sk-real`/`sk-ws-...`（都是占位值）→ 用 `sk-[A-Za-z0-9]` + 排除名单。

Expected: 三条都是 `OK`。若有真输出，立即 `git rm --cached` + 在百炼控制台轮换 key，并说明历史提交如何处理。实测三条均为 OK。

- [ ] **Step 7: 逐条核对 poc 的 44 个测试都有落点，然后删除 poc 与平价脚本**

spec §9 要求 poc 测试全部迁移。删 poc 是不可逆动作，下面这张表就是它的门槛：**逐行确认新位置里确实有那条断言，任何一行对不上都不许执行 `git rm`**。左边是 `grep -n '^def test_' poc/test_*.py` 的全部 44 行输出，一行不少。

`poc/test_validate_homework.py（28 条）`：

| poc 测试 | 新落点 |
| --- | --- |
| test_exact_substring | T4 `test_verbatim_substring` |
| test_dash_rewrite_is_weak_not_fabricated | T4 `test_dash_rewrite_is_tokens_match_not_unsourced` |
| test_invented_word_is_missing | T4 `test_invented_word_is_unsourced` |
| test_emoji_and_brackets_are_stripped | T5 `test_strip_lead_removes_decor_enum_and_connector` |
| test_fabricated_requirement_is_dropped_and_asked | T6 `test_fabricated_requirement_dropped_rest_kept` |
| test_fabricated_subject_blanked_not_shown | T6 同名 |
| test_whole_task_fabricated_drops_item | T6 同名 |
| test_task_may_add_verb_but_not_numbers | T4 `test_verb_completion_allowed_only_for_task` |
| test_wrong_page_number_is_caught | T4 `test_wrong_page_number_caught_even_in_lenient_policy` |
| test_mostly_invented_task_is_caught | T4 `test_mostly_invented_task_caught_even_in_lenient_policy` |
| test_requirements_are_always_strict | T4 `test_only_task_gets_the_lenient_policy` |
| test_omitted_item_becomes_uncovered | T7 `test_dropped_line_becomes_uncovered_pending` |
| test_happy_path_has_no_unresolved | T6 `test_happy_path_no_pending` |
| test_priority_uses_keywords_not_llm | T6 `test_priority_program_overrides_llm` |
| test_no_keyword_means_normal_even_if_llm_says_high | T6 `test_priority_program_overrides_llm`（同一条测两个方向） |
| test_empty_task_item_dropped_with_note | T6 `test_empty_task_dropped_with_note` |
| test_invalid_type_marked_unknown | T6 `test_invalid_type_becomes_unknown` |
| test_non_dict_and_missing_items_rejected | T6 `test_structural_failure_raises_not_silently` |
| test_seq_is_renumbered_after_drops | T6 `test_seq_renumbered_after_drops` |
| test_requirement_already_in_task_is_not_printed_twice | T6 同名（判定层）+ T13 同名（绘制层）——拆两条，两边都得去重 |
| test_independent_requirement_still_shown | T6 `test_fabricated_requirement_dropped_rest_kept`（“其余保留”就是这条性质） |
| test_report_renders_human_readable | 拆两条：T7 `test_pending_has_context_and_related_seq`（上下文进结构）+ T17 `test_prompt_shows_reason_context_and_related_seq`（打印给人看）。`render_report()` 函数本身不迁移，打印责任归 CLI/confirm |
| test_boilerplate_unresolved_not_shown_to_parent | T7 `test_boilerplate_from_model_never_reaches_parent` |
| test_real_homework_never_auto_dropped | T5 `test_boilerplate_prefix_does_not_swallow_a_real_assignment` + T18 同名回归 |
| test_pure_connectors_are_noise_but_deadlines_are_not | T3 `test_deadline_words_are_not_connectors` + T5 `test_deadline_is_never_noise` |
| test_date_scaffold_never_swallows_real_content | T5 `test_date_scaffold_header_is_noise_but_keeps_real_content` |
| test_connector_prefixed_chunk_not_double_reported | T5 `test_connector_prefixed_fragment_not_double_reported` |
| test_boilerplate_filter_still_reports_real_omission | T7 `test_real_omission_still_reported_after_boilerplate_filter` |

`poc/test_parse_homework.py（16 条）`：

| poc 测试 | 新落点 |
| --- | --- |
| test_clean_line_strips_decor_enum_label | T9 同名 |
| test_clean_line_keeps_page_number_starting_with_letter | T9 `test_page_number_starting_with_letter_survives` |
| test_naive_extract_subject_midline | T9 `test_subject_recognised_midline` |
| test_subject_not_split_out_of_material_phrase | T9 同名 |
| test_naive_extract_then_validate_is_clean | T9 `test_naive_then_validate_is_clean` |
| test_priority_survives_naive_path | T9 同名 |
| test_apply_sets_updates_field | T8 `test_manual_correction_is_recorded_in_notes` |
| test_apply_sets_rejects_bad_input | T8 `test_non_whitelist_field_rejected` |
| test_empty_input_yields_no_items | T9 同名 |
| test_unresolved_is_not_self_covering | T7 `test_claimed_text_excludes_pending_by_default` + T8 `test_is_covered_excludes_pending_itself` |
| test_set_clears_unresolved_it_actually_covers | T8 `test_confirmation_loop_is_not_a_dead_end` |
| test_set_on_wrong_item_does_not_clear | T8 `test_correct_on_wrong_target_keeps_pending` |
| test_resolve_flag_discards_non_homework_line | T8 `test_dismiss_only_touches_named_pending` |
| test_resolve_can_quote_the_context_it_sees | T16 `test_dismiss_by_ref_accepts_partial_quote` |
| test_resolve_does_not_touch_other_items_pending | T8 `test_dismiss_only_touches_named_pending` |
| test_resolve_matches_by_substring_not_exact_text | T16 `test_dismiss_by_ref_accepts_partial_quote` |

反过来也要记一笔：**poc 的 `compose.py` / `skeletons.py` 在 poc 里一条自动测试都没有**（全靠肉眼看图）。所以 T11/T12/T13 的 29 条是新增覆盖，不是迁移，平价时不要把它们当成“旧行为变了”。

**门槛用脚本核过，不是靠肉眼数表**：跑 `grep -c '^def test_' poc/test_*.py` 取到 44 条，与上表 44 行逐条对名 → **0 条缺落点**，且表里没有任何一行指向 poc 中不存在的测试。再抽 7 条新落点读其测试体，确认是真断言（不是同名空壳）：`test_verbatim_substring` / `test_task_may_add_verb_but_not_numbers` / `test_omitted_item_becomes_uncovered` / `test_priority_program_overrides_llm` / `test_boilerplate_from_model_never_reaches_parent` / `test_confirm_loop_is_not_a_dead_end`（T8 版）/ `test_non_whitelist_field_rejected`。

**提交顺序是门槛的一部分**：先提交测试（`c4d2822`），再删 poc（`5150d9c`）。反过来做的话，一旦删完才发现某条断言其实没迁移，就只剩 `git reflog` 一条路。

```bash
git rm -r --quiet poc           # 13 个跟踪文件
git rm --quiet parity_check.py  # 平价脚本一次性，通过后即删
git commit -m "chore: 删除 poc（校验规则只保留一份事实来源）"
```

**`poc/.env` 不能跟着走**：它是本地未跟踪的真实凭证文件（`.gitignore` 已覆盖）。`git rm -r poc` 只删跟踪文件，工作区里 `poc/{.env,__pycache__,out}` 会留下——这是对的，删凭证文件属于不可逆且涉密的动作，不在本任务的授权范围内。遗留的 `poc/` 空壳对仓库没有任何影响。

不留 poc 的理由与本项目一路在打的补丁同源：**校验规则存在两份事实来源就一定会漂移**。每条判断（哪些词算套话、哪个字段零容错）都是产品行为，两份实现等于两个产品。

- [ ] **Step 8: 最终全绿 + DoD 自查**

```bash
python3 -m pip install -e ".[dev]" && python3 -m pytest -q
```

Expected: `217 passed, 1 deselected`（T17 结束时是 202；本任务 +8 集成、+7 回归 = 217。`1 deselected` 是默认 `-m 'not network'` 筛掉的网络用例）。

逐条对照 spec §11，实测结论：

1. 全绿且默认零网络 → `217 passed, 1 deselected`，全程无网络调用（集成测试用 `StubExtractor` / `NaiveExtractor`）。
2. 两份原文走通出 2480×3508@300dpi → `test_parse_to_png_for_both_real_samples` 断言 `(2480, 3508, (300, 300))` 且 `Image.open` 复核尺寸。
3. 人工抽查四要素与勾选位 → 用 `FIVE` 生成富数据卡后 `hw render` 出图并逐项目视：5 项均有科目/任务、星标+「重要」落在语文/英语/科学、数学项带「(第12-13页)」与「完成后校对答案」、底部「别忘了」两条、每项有勾选框；`used_placeholder=True`、`issues == []`。
4. 四条不变量各有测试 → T4 的 `ZERO_TOLERANCE` / `ALLOW_VERB_COMPLETION` / `claimed_text` / `is_covered` 各有具名用例，T18 的回归再覆盖双向。
5. 注入杜撰 → 不上图且进 pending → `test_fabricated_field_never_reaches_the_card`：`requirements == []`、pending 为 `["用铅笔"]`、`NeedsConfirmation`、`rglob("*.png")` 为空。
6. 注入遗漏 → 进 pending → `test_omitted_item_becomes_pending`：漏掉数学项后 pending 含「第12-13页」与「校对答案」。
7. pending 非空 render 退出码 2 且无文件 → `test_pending_blocks_render` 与 `test_confirm_loop_then_render_opens_the_gate` 的 `EXIT_PENDING` 段。
8. 无凭证痕迹 → Step 6 三条命令全 `OK`（`.env` 无跟踪、历史无 `.env`、源码无真实 key）。
9. poc 已删除 → `5150d9c` 删除 13 个跟踪文件；`git ls-files poc` 为空。

- [ ] **Step 9: Commit**

测试与 poc 删除已按上面的顺序分两次提交。本任务的收尾提交只含 plan 与 ledger 的同步：

```bash
git add docs/superpowers/plans/2026-11-06-homework-compass-core.md
git commit -m "docs: T18 计划同步（集成/回归/平价/删除 poc 的实测校准）"
```

实际提交信息为 `test: 全链路集成、poc 回归与两份真实原文 fixture`（初稿写「四条 poc 回归」，实测是 7 条测试覆盖 4 个 bug 类，`four` 与测试数不符，按「commit message 只描述事实」的原则改掉）。

---

## 遗留问题（如实记录，不在本版解决）

1. **关键词优先级仍是词表级近似**：「明天」出现在"明天开始练习"里也会判高优。真需要语义级判断时，得让模型输出信号而不是结论——本版只要"漏不掉"，宁可多标。
2. **兜底解析器不拆字段**：`NaiveExtractor` 只按句拆条，quantity/requirements 恒空，所以离线路径的卡面信息密度低于 LLM 路径。这是刻意的：降级路径负责"能用"，不负责"好用"。
3. **OCR 只有接口、没有真实板书照片验证过**。`test_real_extract` 系列也只覆盖文本抽取。首次真图 OCR 必须人工比对识别文本与图片。
4. **同一模型两次输出可能不同**（`temperature=0` 也不保证确定性）。这不是缺陷而是前提：所有信任来自校验层，不来自模型。
5. **6 项以上作业会抛 `LayoutError`**，分页在 spec 之外。用户可见的正确提示是"换骨架或分页"，具体做法留给生图/多骨架那个 spec。
6. **皮肤只影响 accent 色**，8 款皮肤的实际视觉差异要等底图。本版 `--skin` 参数存在但不产生视觉差别，README 已按"预览"定位。
