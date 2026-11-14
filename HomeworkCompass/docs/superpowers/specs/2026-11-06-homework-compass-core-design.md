# 每日作业目标生成器 — 核心包设计文档（解析 · 校验 · 排版）

日期：2026-11-06
状态：待评审
上游文档：`每日作业目标生成器-方案设计文档.md`（本文档不重复其产品定义，只覆盖其技术落地）

---

## 0. 范围

完整产品横跨五个子系统。本文档只覆盖其中三个，其余四个各自另立 spec：

| 子系统 | 本文档是否覆盖 |
|---|---|
| ① 作业解析 + 机械校验 | ✅ |
| ② 版式骨架坐标契约 | ✅（机制 + 1 个骨架） |
| ③ 排版渲染（文字层） | ✅ |
| ④ 生图 API 与底图模板缓存 | ❌ 另立 spec |
| ⑤ 家长操作界面与偏好存储（Web） | ❌ 另立 spec |

**本版交付形态**：一个边界干净的 Python 库 + 一个作为其第一个使用者的命令行工具。库不做任何 IO 交互，CLI 只做薄适配层。未来 FastAPI 后端是库的第二个使用者，不需要改动库。

**本版明确不做**：调用生图 API、其余 5 个骨架 × 8 款皮肤、作业项超过 10 项的分页、Web 界面、数据库与偏好云同步、PDF 导出。

### 前置事实（已由 poc 实测，不再重复验证）

- 双层架构（AI 出无文字底图 + 程序绘中文）成立；生图侧留白控制、竖版比例、分辨率上限已核实。
- 「抽取 + 机械校验」方案在 2 份真实老师原文上跑通：5 项全部可溯源、0 杜撰、0 遗漏。
- 纯 LLM 抽取不可单独采信：它会静默杜撰（补出原文没有的"用铅笔"）也会静默漏项（把"明天带美术材料"的"明天"丢掉）。这两种错误都不报错，必须由程序机械核对。

---

## 1. 不可协商的产品约束

来自上游文档，落到代码层面即为：

1. **零杜撰**：任何字段值若在原文找不到出处，不得上图，必须转为待确认项。
2. **零遗漏**：原文每个实义片段必须被某个字段认领，未认领者转为待确认项。
3. **闸门**：待确认项非空时禁止出图，不存在"先生成再说"。
4. **文字全部由排版引擎绘制**，禁止依赖生图模型写中文。
5. **A4 竖版 2480×3508 @300dpi**，页边距 ≥10mm，正文 ≥14pt 等效字号。

---

## 2. 架构与依赖方向

```
老师原文/OCR 文本
      │
      ▼
 extractor（可注入：LLM / 离线兜底 / 测试桩）──► 候选结构 dict
      │
      ▼
 validate（溯源 + 覆盖两道机械校验）──► ParsedHomework（items + pending + report）
      │
      ├─ pending 非空 ──► 回问家长 ──► correct()/dismiss() ──► 新的 ParsedHomework
      ▼
 compose（骨架坐标契约 + Pillow 文字层）──► RenderResult（PNG 路径 + issues）
```

`pipeline.py` 是对外 API 的安放处：`parse_homework()` / `correct()` / `dismiss()` / `render()` 四个函数在此定义，它们只**编排** `parsing.*` 与 `layout.*`，自己不含业务规则。命名上刻意不叫 `render.py`，避免让人误以为“解析”发生在排版里。

模块依赖方向严格单向，`import` 不得反向：

```
cli/  →  pipeline  →  parsing.* , layout.*  →  models , errors
parsing.*  与 layout.* 互不依赖
llm_client 只被 parsing.extract 依赖
```

理由：校验层必须能在没有排版、没有网络、没有 CLI 的情况下被单独测试和复用。

---

## 3. 项目结构与依赖

```
HomeworkCompass/
├── pyproject.toml
├── README.md
├── src/homework_compass/
│   ├── __init__.py          # 只导出 public API，内部模块不对外
│   ├── models.py            # 中枢数据类型
│   ├── errors.py            # 异常层级
│   ├── config.py            # 配置加载与优先级
│   ├── llm_client.py        # DashScope chat 传输 + 鉴权
│   ├── parsing/
│   │   ├── __init__.py
│   │   ├── extract.py       # LLM 抽取 + 离线兜底 extractor
│   │   ├── validate.py      # 机械校验（承重墙）
│   │   └── vocabulary.py    # 词表：套话 / 连接词 / 高优信号
│   ├── layout/
│   │   ├── __init__.py
│   │   ├── skeleton.py      # 坐标契约 + 提示词构建
│   │   ├── compose.py       # Pillow 文字层
│   │   └── fonts.py         # 字体解析 + 字形覆盖探针
│   ├── pipeline.py            # 对外 API 编排层，不含业务规则
│   └── cli/
│       ├── __init__.py
│       ├── main.py          # argparse 适配层
│       └── confirm.py       # 交互式销账，全项目唯一碰 tty 的模块
└── tests/
    ├── unit/
    ├── integration/
    └── regression/
```

### 依赖策略

- **运行时依赖只有 Pillow**。开发依赖只有 pytest。
- 不引入 pydantic（Python 3.13 的 `dataclass(slots=True)` + 手写构造校验足够，且校验规则本身就是我们的领域逻辑，不该外包给通用 schema）。
- 不引入 typer / click / rich（argparse + 纯文本输出够用，CLI 是薄层，不值得为它加依赖）。
- 配置文件解析用 stdlib `tomllib`（只读，无需写 TOML 的库）。

### 为什么用 `src/` 布局

poc 里到处是 `sys.path.insert(0, ...)`，转正必须消灭这种 hack。`src/` 布局强制"先安装再导入"，测试跑的是真实安装态，不会出现"在目录里能跑、装了就挂"。

---

## 4. 数据模型

中枢数据从裸 dict 升级为带类型的结构。字段名与上游文档的 JSON schema 保持一致，并作为其**超集**——poc 期间产出的 JSON 文件必须能被新库读入。

```python
class TraceLevel(str, Enum):
    VERBATIM      = "verbatim"       # 去标点后是原文子串
    NORMALIZED    = "normalized"     # 连接符/写法被改写
    TOKENS_MATCH  = "tokens_match"   # 词元全命中、顺序不成立
    PARTIAL       = "partial"        # 仅 task 允许：数字全中 + 汉字重合≥0.6
    UNSOURCED     = "unsourced"      # 无出处 → 拒绝采信

class PendingReason(str, Enum):
    FABRICATED      = "fabricated"        # 抽取结果里有、原文里没有
    UNCOVERED       = "uncovered"         # 原文里有、抽取结果里没有
    AMBIGUOUS       = "ambiguous"         # 模型自己表示拿不准
    OCR_UNVERIFIED  = "ocr_unverified"    # OCR 来源，强制确认

# 以上四种全部是**阻断型**：只要存在就不得出图。
# NORMALIZED / TOKENS_MATCH / PARTIAL 这三类“已采信但建议扫一眼”的情况
# 不得进入 pending，否则一个正常的 P12-13→P12–P13 规范化就会卡死整个流程，
# 而“每天要确认一堆已经抽对了的项”正是上游文档要避免的事。
# 它们只进 report.advisories，只提示、不阻断。

@dataclass(slots=True)
class HomeworkItem:
    seq: int
    subject: str
    task: str
    quantity: str
    requirements: list[str]        # 上图显示的要求（已去除与 task 重复者）
    requirements_all: list[str]    # 校验通过的全部要求（供优先级判定与审计）
    priority: Literal["high", "normal"]
    priority_signals: list[str]
    estimated_minutes: int | None
    type: str
    provenance: dict[str, TraceLevel]   # 每个字段是怎么来的

@dataclass(slots=True)
class PendingItem:
    id: str                    # 稳定标识，销账靠它，不靠文案匹配
    text: str                  # 给家长看的原文片段
    reason: PendingReason
    source_sentence: str       # 出自原文哪一句
    related_seq: int | None    # 关联到第几项，供 CLI 提示"补进第 4 项"

@dataclass(slots=True)
class ValidationReport:
    """溯源与覆盖的完整审计结果。只用于展示与排错，不作为出图闸门依据。"""
    traced: list[TraceRecord]        # 每个字段的判定结果（where/value/level）
    advisories: list[TraceRecord]    # 已采信但非 VERBATIM 的项，建议扫一眼
    uncovered: list[str]
    priority_overrides: list[dict]
    notes: list[str]
    stats: dict[str, int]


@dataclass(slots=True)
class ParsedHomework:
    date: str
    student_name: str
    slogan: str
    items: list[HomeworkItem]
    extras: list[str]
    pending: list[PendingItem]
    source_text: str
    report: ValidationReport

@dataclass(slots=True)
class RenderResult:
    path: Path
    width: int
    height: int
    dpi: tuple[int, int]
    issues: list[RenderIssue]
    used_placeholder: bool     # True 表示底图是占位图，不是可打印成品
```

`PendingItem` 取代 poc 里的裸字符串列表。这是"库只返回结构、界面各自驱动 UI"的前提：裸字符串无法让 Web 端渲染出"该改哪一项"的动作，也无法稳定销账。

`unresolved` 这个 JSON 字段名保留兼容：读取时若 `pending` 与 `unresolved` 同时存在，以 `pending` 为准；`unresolved` 仅作为 `pending` 的文本投影写出，供旧工具消费。两个字段内容冲突时不得静默合并，直接报错。

---

## 5. 校验层（承重墙）

### 5.1 三条不变量

写在 `validate.py` 模块 docstring 顶部，任何改动都必须先证明没有破坏它们：

1. **溯源**：字段值必须在原文有出处，否则不采信。
2. **覆盖**：原文每个实义片段必须被认领，否则回问家长。
3. **闸门**：`pending` 非空 → 上层拒绝出图。

### 5.2 字段策略表

poc 用 `strict: bool` 参数表达这件事，正式版升级为显式策略表——因为"哪个字段零容错"本身就是产品判断，不该藏在一个布尔参数里。

```python
FIELD_POLICY: dict[str, TracePolicy] = {
    "subject":      TracePolicy.ZERO_TOLERANCE,          # 科目张冠李戴比漏一项更隐蔽
    "quantity":     TracePolicy.ZERO_TOLERANCE,          # 页码/数量错一个字就是错
    "requirements": TracePolicy.ZERO_TOLERANCE,          # 凭空多出的"用铅笔"最伤信任
    "extras":       TracePolicy.ZERO_TOLERANCE,
    "task":         TracePolicy.ALLOW_VERB_COMPLETION,   # 原文「练习册」→「完成练习册」放过
}
```

`ALLOW_VERB_COMPLETION` 的判定前提不可放宽：**数字与字母词元必须全部命中原文**，且汉字重合度 ≥0.6。这保证"页码写错""任务整个编出来"仍然被拦住。

"命中原文"有一条例外：值里的词元可以是原文**相邻词元**的拼接（`1213` = `12` + `13`，模型只是去掉了分隔符）。没有这条例外，`P12-13` 被写成 `P1213` 这种正确数据会被扔进 pending——那比漏判更烦人。细节见 §5.3。

### 5.3 溯源判定顺序

按代价从低到高短路，命中即返回：

```
VERBATIM → NORMALIZED → TOKENS_MATCH → (仅 task) PARTIAL → UNSOURCED
```

子串/子序列判定**之前**先过一道词元闸，就是 §5.2 那句「数字与字母词元必须全部命中原文」：`norm` 会把 `P12-13` 压成 `p1213`，于是 `P12`、`P1` 这类前缀也都是原文的子串；不先卡词元，被截断的页码会被判成逐字命中。词元闸留一个例外：值里的词元可以是原文**相邻词元**的拼接（`1213` = `12` + `13`，模型只是去掉了分隔符），否则正确数据会被扔进 pending。这个"相邻"是在词元序列上相邻——汉字不占词元位，所以「12页13页」的 `1213` 也算命中（宁可放过，不可把正确数据判成杜撰）。

比对前还要先去掉列表序号（`1.`、`2、`、`（1）`、`1)`）：序号里的数字不是内容，留着会让截断的页码蒙混过关。序号规则要窄，宁可漏剥不可错剥——`P12-13.` 句末的 `13.` 是页码的一部分，`1、2页` 的 `1、` 后面是数字（页码范围，不是条目序号），`抄写生字（2）遍` 的 `（2）` 前面是汉字（是数量，不是序号）。源侧与值侧按同一套规则剥：模型逐字摘录原文时会带上 `1.`，只剥一侧会把忠实的摘录判成无出处。

`TOKENS_MATCH` 这一级存在的原因是真实误判：模型把 `P12-13` 规范成 `P12–P13` 时，子串与子序列判定都会失败，若没有词元级兜底就会把正确数据扔进 pending，比漏判更烦人。词元必须从**原文**切，不能从去标点后的字符串切（否则 `P12-13` 被粘成 `1213` 对不上）。

### 5.4 覆盖率算法

双粒度，缺一不可：

- **片段（fragment）**：按句子分隔符切，用于给家长展示上下文。
- **词块（chunk）**：片段再按逗号/顿号/冒号/空白切，用于检测——否则一个已认领的词就能掩盖整句遗漏。

判定：某 chunk 在"已认领文本"里溯源不通过 → 计入 `UNCOVERED`，同时记录它所属的 fragment 作为上下文。

**已认领文本**包含 subject（原文常写"英语听读打卡"，拆成 subject+task 后若不拼回去会误报遗漏）。

### 5.5 词表（`vocabulary.py`）

三类词表是产品行为，不是实现细节，因此独立成可审计数据，每个条目带一句存在理由：

```python
BOILERPLATE: frozenset[str]   # 客套/标题词：不构成作业内容
CONNECTORS: frozenset[str]    # 话语连接词：单独成句时无信息量
PRIORITY_MARKERS: dict[str, str]  # 高优信号词 → 为什么它意味着重要
```

三条硬规则：

1. `CONNECTORS` 只收"怎么写都不是任务"的词。"今天/明天"是截止时间，**不得**收录。
2. `PRIORITY_MARKERS` 分两类：事件标记（签字/背诵/打卡/测验/需带/自带）与截止时间（明天/后天/周X）。**"准备""重点"这类高频动词从表里移除**——poc 实测"准备好彩泥和剪刀"因"准备"被判高优，是误判。
3. 噪声词表全项目唯一。上游解析器与校验器必须复用同一张表，否则会出现"解析器丢了、校验器却报遗漏"的矛盾。

### 5.6 采信与降级规则

| 情况 | 处置 |
|---|---|
| task 为 `UNSOURCED` | 整项丢弃，原文片段转 pending |
| subject 为 `UNSOURCED` | 科目置空，pending 说明"科目在原文找不到" |
| requirement 为 `UNSOURCED` | 仅丢该条要求，其余保留 |
| `NORMALIZED`/`TOKENS_MATCH`/`PARTIAL` | 采信，并进 `report.advisories` 标黄提示（**不**进 pending，不阻断） |
| priority | **一律由程序按词表判定，覆盖模型给出的值** |

### 5.7 销账规则

`correct(hw, seq, field, value)` 与 `dismiss(hw, pending_id)` 返回新对象。

销账口径与提出它的口径**必须一致**：`correct()` 之后重新计算该 pending 是否已被"已认领文本"承接，承接则自动销账；未承接则保留。这避免了 poc 初版的死胡同——家长改完字段但 pending 永远清不掉，图永远生不成。

两个不可回退的细节：

- 销账靠 `pending_id`，不靠文案子串匹配（poc 用 `norm(r) in norm(u)`，家长改一个字就对不上）。
- 计算"已认领文本"时**必须排除 pending 自身**，否则待确认项会自己认领自己，永远销不掉。

### 5.8 要求去重

模型常把整句当 `task`、又把句尾要求单列一份，导致卡面上同一行字印两遍。规则：`requirements` 中 norm 后已包含于 `task + quantity` 的条目，从**显示列表**移除，但保留在 `requirements_all` 中——优先级判定仍用完整文本，不能因为去重而漏掉"签字""打卡"信号。

---

## 6. 排版层与坐标契约

### 6.1 骨架即数据

`Skeleton` 由若干 `Zone`（归一化矩形 `x/y/w/h`，原点左上）组成，类型有 `TITLE / STATION / EXTRAS / REWARD`。

**单一事实来源不变量**：同一份 Zone 数据同时驱动生图提示词构建与文字落位。二者物理上不可能对不上——这是整个双层架构最大的风险点（AI 留白位置与写字位置漂移）。

### 6.2 `build_prompt()` 本版保留但不调用生图 API

理由：它就是上述不变量的另一半。删掉它，坐标契约就退化成"只有文字层用得上的坐标表"，下个 spec 接生图时提示词必然另写一份，契约当场失效。它的测试是离线的：

- 断言每个 Zone 都在提示词里被空间描述；
- 断言提示词包含"框内无任何文字/字母/数字"的约束；
- 断言不传文字内容进去。

本版只转正 1 个骨架（闯关游戏地图，6 个关卡位），骨架注册表为字典结构，其余 5 个后续以纯数据方式追加。

### 6.3 硬约束（写成断言，不靠人记）

| 约束 | 违反时 |
|---|---|
| 底图先超分至 2480×3508，**再**绘文字 | 顺序颠倒会让文字发虚，直接违反"正文≥14pt清晰可读"。`compose` 入口断言画布尺寸 |
| 页边距 ≥10mm | Zone 定义期校验，构造骨架即失败 |
| 正文不低于 12pt 下限 | 低于则报 `RenderIssue`，不硬塞 |
| 项数 > 骨架留白数 | 抛 `LayoutError`，不静默截断 |
| 文字外接矩形落在 Zone 内 | 报 `RenderIssue` |
| 折行不得让右括号等标点孤零零出现在行首 | 行首禁则处理 |

`RenderIssue` 一律向上冒泡并由 CLI 打印，**绝不静默放行**。

### 6.4 字体

poc 依赖回退链碰运气，且实测本机 `PingFang.ttc` 已不存在（靠 `Hiragino Sans GB` 兜住）。正式版 `fonts.py`：

1. 按配置优先级解析字体路径，候选表可被配置覆盖；
2. **字形覆盖探针**：用样本汉字渲染，检查墨迹非空且不是豆腐块；
3. 全部失败则抛 `FontError` 并列出已尝试路径。

### 6.5 占位底图必须诚实标注

本版不接生图，底图来源只有两种：`--base <png>` 指定真实底图，或不传而使用带坐标辅助线的占位图。后者 `RenderResult.used_placeholder=True`，CLI 大声提示"这是排版预览，不是可打印成品"。不加水印（上游文档禁止），但也不假装它是成品。

---

## 7. 抽取层与 LLM 客户端

### 7.1 extractor 是注入的协议

```python
class Extractor(Protocol):
    def __call__(self, raw_text: str, *, date: str, name: str) -> dict: ...
```

三个实现：`LlmExtractor`（qwen-plus）、`NaiveExtractor`（离线兜底，刻意做笨，只按行拆条不拆字段）、`StubExtractor`（测试）。校验层不知道上游是谁。

这把 poc 里的 `--no-llm` if 分支变成了正式设计：降级路径与主路径共用同一套校验。

### 7.2 提示词约束

模型被当作**不可靠的抄写员**来约束：所有字段值必须逐字摘录；拿不准的放进 `unresolved`；不得输出 `priority`（程序会覆盖）；`estimated_minutes` 不确定就写 null。`temperature=0`，`response_format={"type":"json_object"}`（提示词已含 JSON 字样，否则接口报错）。

### 7.3 OCR 路径

本版保留 OCR 接口但不做界面。规则不可妥协：**任何来自 OCR 的输入，强制产生一条 `OCR_UNVERIFIED` pending**，不因"看起来抽对了"而静默放行。

### 7.4 传输与鉴权

- 只用标准库（`urllib`），不为 HTTP 加依赖。
- `DASHSCOPE_API_KEY` **只从环境变量读取**。配置模块里不存在读取该字段的代码路径——从结构上杜绝凭证误提交，而不是靠"建议不要写"。
- 错误信息必须可操作：401 提示 key 无效/需轮换与域名问题，404 提示端点，超时提示重试与调大 timeout。
- 已知坑（写入模块 docstring）：业务空间维度 key 与老域名的兼容关系；图像 URL 24 小时失效（本版不生图，但下个 spec 必须立刻下载落盘）。

---

## 8. CLI

### 8.1 子命令

```
hw parse   --file raw.txt --name 小宇 --out hw.json
hw confirm hw.json
hw render  hw.json --skeleton quest-map --skin dinosaur [--base b.png] --out out/
hw zones
hw prompt  --skeleton quest-map
```

命令名用 `hw`：每天要敲的命令，短比正式重要。`hw parse --image` 走 OCR 路径。

### 8.2 交互确认

`confirm.py` 是全项目唯一读取 tty 的模块。逐条展示 pending：

```
[1/2] 疑似遗漏  「明天带美术材料」
      出自：明天带美术材料：彩泥
      关联：第 4 项（美术）
   (e) 补进第 4 项  (d) 不纳入  (s) 跳过保留  (q) 退出并保存
```

每次操作调用库的 `correct()` / `dismiss()`，**CLI 不自己实现任何校验或销账逻辑**。

`(e)` 的展开：选定目标项后询问要写哪个字段（默认 `task`），输入新值，然后调 `correct(hw, seq, field, value)`。销账结果由库给出，CLI 只负责把“已销账/仍待确认”读回来展示。

**非 tty 时拒绝交互**：输出结构化 JSON + 退出码 3。这保证它能在 AI 助手对话里用（上游文档阶段 1 形态），也能被未来 Web 端复用。

### 8.3 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 2 | 存在 pending，拒绝出图 |
| 3 | 解析产生了 pending |
| 4 | 参数或字段白名单错误 |
| 5 | API 或字体错误 |

字段白名单：`subject / task / quantity / requirements / priority / type`。其余一律拒绝并报错。

### 8.4 配置

优先级：命令行 > 环境变量 > `config.toml` > 内置默认。

`profile.toml` 存姓名 / 默认骨架 / 默认皮肤（上游文档"一次设置、长期复用"），纯文件实现，不引数据库。凭证不在任何配置文件里定义。

---

## 9. 测试策略

| 层 | 内容 | 网络 |
|---|---|---|
| unit | 校验规则、词表、坐标契约、字体探针、排版不变量 | 无 |
| integration | `parse → confirm → render` 全链路，用 `StubExtractor` 注入 | 无 |
| regression | poc 期间 4 个真实 bug，各一条具名测试，注释写明"曾经怎么坏" | 无 |
| network | 真实 LLM 抽取质量 | 打 `-m network`，**默认不跑** |

poc 的 44 条测试全部搬迁进新结构。网络测试默认排除的理由：花钱且不稳定，真实 LLM 冒烟由人工执行并留证据。

**不做像素 golden image**。字体版本或 Pillow 小版本一变就全红，维护成本压垮收益。改测版面不变量（文字外接矩形在 Zone 内、无孤标点、要求不重复、超量抛错）。

### 四条回归测试必须存在

1. `test_confirmation_loop_is_not_a_dead_end` — 补完字段后 pending 必须能清掉。
2. `test_boilerplate_never_reaches_parent` — 套话不得转成家长确认项。
3. `test_real_homework_never_auto_dropped` — 真作业绝不被当套话吞掉（危险方向）。
4. `test_requirement_not_printed_twice` — 同一行字不印两遍，但优先级判定仍生效。

---

## 10. 迁移与 poc 处置

1. 初始化 git 仓库（当前**尚无版本控制**），**提交 1**：上游方案文档、本 spec、`.gitignore`。
2. **提交 2（基线快照）**：把 `poc/` 入库，提交信息明写“poc 基线，仅作平价比对用，将被删除”。

   这一步不可省：不先把 poc 存进版本库，“平价校验”就无法重现和审校，第 5 步的删除也变不成一个真实提交。同时，它把“校验规则只有一份”这个约束落实成了一个可回退的 diff。`poc/.env` 已被 `.gitignore` 排除，**入库前必须用 `git status` 确认它没出现在待提交列表里**。
3. 按本文档实现 `src/` 包。
4. **平价校验**：两份真实原文分别过 poc 与新包，比对 items 数、pending 内容、priority 判定、成图尺寸与 DPI。必须一致。

   测试用原文不必重新构造：poc 产出的 `poc/out/hw_raw1.json` 与 `hw_raw2.json` 里已经完整保存了 `source_text` 字段，直接抽取为 `tests/fixtures/raw1.txt`、`raw2.txt` 即可。平价校验完成后这两个文件必须仍然得到与 poc 时代一致的结论：raw1 产生 1 条阻断型 pending（模型丢了“明天”），raw2 产生 0 条。
5. 平价通过后**删除 `poc/`**，单独一个提交。

不留 poc 的理由与本项目一路在打的补丁同源：**校验规则存在两份事实来源就一定会漂移**。当前每条判断（哪些词算套话、哪个字段零容错）都是产品行为，两份实现等于两个产品。

`.gitignore` 已确保 `.env` 在任何目录都不入库。另需提醒：会话中曾明文出现过的 API key 应在服务端轮换。

---

## 11. 验收标准（Definition of Done）

同时满足才算完成：

1. `pip install -e .` 后 `pytest` 全绿，且默认不发起任何网络请求。
2. 对 `tests/fixtures/` 里两份真实原文，`hw parse → hw confirm → hw render` 走通，产出 2480×3508@300dpi PNG。
3. 人工抽查成品图：每项作业四要素齐全（科目/内容/数量/要求）、高优项有视觉强调、底部有"别忘了"条、每项旁有勾选位。
4. 校验层四条不变量各有测试覆盖。
5. 注入一条杜撰数据（原文没有"用铅笔"）→ 该项不上图且进入 pending。
6. 注入一条遗漏（原文 5 项只抽 4 项）→ 缺失片段进入 pending。
7. pending 非空时 `hw render` 退出码为 2 且不产出文件。
8. 仓库中不存在任何真实凭证；`git log` 无 `.env` 痕迹。
9. poc 已删除，或明确记录为何保留。
