# AI-Agent 项目开发历程报告

> 数据来源:Git 历史(2026-02-06 至 2026-03-31,共 41 个提交)、`memory-bank/` 长期记忆库、当前代码与配置文件状态。
>
> 总览:项目从 2026-02-06 启动至今约 8 周,经历 **奠基 → 横向扩能 → 异步与多 Provider 化 → 视觉新能力 → 营销自动化 → 文档与运维收束** 六个阶段;主线为「AI 服务能力」,旁支为「营销引流」。

---

## 一、项目启动阶段(2026-02-06 ~ 2026-02-08)

### 1.1 时间范围与节奏

3 天集中奠基,共 12 个提交,主要单日:

- 2026-02-06:7 个提交,搭建仓库骨架(`61d4449` ~ `df8b19e`)
- 2026-02-07:4 个提交,补 OCR 多引擎与测试(`a3a97d2` ~ `b6bf2f6`)
- 2026-02-08:1 个提交,日志与 dotenv 加固(`c0c2506`)

### 1.2 核心目标

依据 `memory-bank/0-project-brief.md`:

> 本仓库为 **AI Agent 与作业辅导能力**(OCR、故事/插图/解题引导、API 等)的工程实现;营销自动化为引流辅助。

定位为**主后端调用的 Python AI 服务层**(参见 `README.md` "服务定位"),不承担用户/作业 CRUD、上传存储等业务职责。

### 1.3 初始架构(单日成型)

`2026-02-06` 通过 7 个原子提交按层次铺开:

| 提交 | 引入能力 | 关键文件 |
|---|---|---|
| `61d4449` chore | 项目基础(规则、依赖、`.env.example`、README) | `requirements.txt`、`.cursorrules` |
| `251633d` feat | LCEL + ChatTongyi 最小可运行示例,验证 LangChain 1.0 + DashScope 路径 | `example.py` |
| `ea1723e` feat | FastAPI 应用、路由、请求体 | `api/main.py`、`api/schemas.py` |
| `3ead8aa` feat | OCR 模块(百度 OCR + 题目识别) | `ocr/service.py`、`ocr/baidu_ocr.py`、`ocr/postprocessing/` |
| `609ee33` feat | 内容生成(故事、插图、解题步骤) | `content_generation/story_generator/`、`solution_generator/`、`illustration_gen/` |
| `3eb1bfb` feat | 工具与语音合成 | `voice_synthesis/aliyun_tts.py`、`utils/` |
| `df8b19e` docs | 文档与图片资源 | `docs/`、`imgs/` |

**一日成形的初始架构图**:

```
api/  ──┐
        ├─ ocr/                  (预处理 → 引擎 → 后处理)
        ├─ content_generation/   (故事 / 插图 / 解题)
        ├─ voice_synthesis/      (Aliyun TTS)
        └─ utils/                (env、logging)
configs/ + .env(模板) → 全部从配置/环境读取,无硬编码密钥
```

技术栈奠基(详见 `memory-bank/1-tech-stack.md`):**Python 3 + FastAPI + LangChain 1.0 LCEL + ChatTongyi/Qwen + DashScope + 百度 OCR**;`requirements.txt` 锁定 LangChain ≥1.0、`langchain-dashscope`、`langchain-milvus`、`langgraph` 等。

---

## 二、功能迭代阶段(2026-02-07 ~ 2026-03-30)

按时间线列出主要能力发布。

### 2.1 OCR 多引擎与测试基线(2026-02-07)

- **`face517` feat(ocr)**:OCR 引擎从单一百度扩展为可选 `baidu | paddle | qwen_vl`,通过 `OCR_ENGINE` 环境变量切换。代码证据:`ocr/service.py:24-35` 的 `_load_config` 与 `:101-171` 的 `_recognize_qwen_vl`。
- **`b6bf2f6` feat(tests)**:首批单元、接口、e2e 测试入库,含 `originalText` 明细输出能力,确立"被测函数 + mock 边界 + 端到端"的三层测试结构。

### 2.2 第一波内容能力扩展(2026-02-22,单日 5 提交)

集中发布语音、OCR 插图截取、插图生成、API 扩展:

- **`574201e` feat(tts)**:阿里云 TTS 自检、长文案分批请求 + 音频拼接(单次上限默认 300 字,可由 `ALIYUN_TTS_MAX_CHARS_PER_REQUEST` 覆盖,见 `voice_synthesis/aliyun_tts.py:20`)。同时引入 `pytest.ini` 过滤 `aliyun-nls` 的 `ssl.PROTOCOL_TLS` 弃用警告。
- **`2f69682` feat(ocr)**:OCR 题目识别后追加 `ocr/figures.py` 插图截取,8 个文件、+780/-65 行,是该阶段最大提交。
- **`7b62d7e` feat(illustration)**:`configs/content_generation.yaml` 与 `content_generation/illustration_gen/image_gen.py`,首次接入漫画插图生成。
- **`86315f2` feat(api)**:`/voice/synthesize`、`/content/illustrate` 路由与 schema 上线。
- **`3c37c00` chore**:补 `gunicorn.conf.py`,从开发单进程切到生产多进程能力。

### 2.3 插图能力深化(2026-02-24 ~ 2026-02-28)

围绕"漫画分镜 + 多 Provider"快速演进:

| 日期 | 提交 | 关键变化 |
|---|---|---|
| 02-24 | `2024ec3` feat(illustration) | 多分镜 + 对话框 + Midjourney `--cref` 参考图 |
| 02-24 | `4365c0b` feat(api) | `/content/illustrate` 改为 `async` + `asyncio.wait_for`,超时从 `content_generation.yaml` 读取 |
| 02-25 | `e69ba3a` feat(illustration) | 兴趣驱动角色(`interests` 贯穿 schema → API → 生成器),Provider 感知 prompt |
| 02-25 | `e9ce445` chore(config) | Gemini Provider 行为文档化 |
| 02-26 | `bdf2cb6` fix(voice) | Aliyun TTS 改用 certifi CA(典型生产环境证书问题) |
| 02-28 | `ebf08a1` feat(illustration) | Gemini 配置项与 prompt 对齐 |
| 02-28 | `b2c8a9c` refactor(illustrate) | 接口收敛:**只接受** `illustration_prompts` 与 `interests`(其余从 yaml 读取),并打印 request body 用于排查 |

`b2c8a9c` 是首个明确的 **API 契约收紧** 重构:把"什么从 API 入参 / 什么从配置"做了明确切分,后续接口风格与之保持一致。

### 2.4 漫画分格新能力(2026-03-10 ~ 2026-03-11)

- **`20473a5` feat(extractor)**:`tools/comic_panel_extractor.py`,基于 OpenCV 边框检测把整张漫画切为多张分镜。
- **`df6c96e` feat(api)**:暴露 `/agent/img_extractor` 接口。
- **`fd9fbcf` chore**:输出路径与文件属主(`www:www`)调整,服务化到生产部署形态(代码见 `api/main.py:294-335` 的 `_chown_recursive`)。
- **`9e7556a` fix**:URL 拉取支持重定向与 HTTP 回退。
- **`ebc634b` feat(extractor)**:分镜检测稳健性与多种网格布局支持。

5 个提交在两天内完成"工具 → API → 部署 → 健壮性 → 布局扩展"完整链路。

### 2.5 Coze 工作流接入(2026-03-27)

**`5dbeb14` feat(scripts)**:`scripts/call_coze_workflow.py` 异步工作流执行器,使用 `cozepy` + 轮询 + 结构化输出,引入 `--max-wait-seconds` 适配长耗时任务。这是项目首次引入**外部低代码工作流**作为内容生产源。

### 2.6 营销/小红书流水线(2026-03-30,单日 8 提交)

3-30 是项目第二大单日改动。按提交序:

1. **`c754bab` feat(marketing)** — `marketing/xiaohongshu/` 全量入库:`theme.py`、`composer.py`(五段式正文)、`sign.py`(MD5)、`client.py`(可选 OAuth/`common_controller`)、`diary.py`(JSONL + 日 MD)。`config/xhs_campaign.yaml` 与 `config/xhs_api.yaml` 落地。
2. **`9022ba7` docs(memory-bank)** — **首次建立长期记忆库**:`0-project-brief` 至 `5-decision-log` 六份文档全数初始化。这是项目首次显式承认"AI 协作需要可读项目上下文"。
3. **`8adb4fa` chore(tools)** — 引入 `tools/xiaohongshu-mcp/`(Docker + ARM64 离线 Chromium),为后续"MCP 自动发帖"路径打基础。
4. **`2137296` chore(cursor)** — 项目级 MCP 客户端配置。
5. **`c9e6620` chore(env)** — `.env.example` 增补 Coze 与小红书变量;`.gitignore` 屏蔽 AccessKey CSV(密钥安全加固)。
6. **`fe6ca4b` feat(coze)** — 每日 Coze 工作流脚本扩展,题目库与主题扩展 + `daily_coze_config.json`。
7. **`f28e25d` fix(content_generation)** — 插图对白规则:**先中文表述再写入英文 prompt**,避免直接英文台词,体现儿童教育产品的语言规范。
8. **`e02bc42` docs(cursor)** — `.cursorrules` 扩充 memory-bank 用法、LangChain 约定、AI 服务目录结构。

`memory-bank/5-decision-log.md` 在此期间记录了 3 条关键决策(全部 2026-03-28):

> **决策 #3**:**正式发布**经 **xpzouying/xiaohongshu-mcp**(本仓库 `tools/xiaohongshu-mcp`),`client.py`/`xhs_api.yaml` 仅作可选遗留。

这条决策在隔天(03-31)的代码改动里全面落地,体现"决策日志 → 行动"的快速闭环。

---

## 三、技术升级阶段

项目尚处早期,无大版本升级,但若干**跨横向**的基础设施加固集中在以下提交:

### 3.1 配置与环境加载(2026-02-08, `c0c2506`)

> fix: dotenv 解析警告与日志输出(safe_load_dotenv、logs 目录、LOG_LEVEL/LOG_DIR)

- 引入 `utils/env.py:safe_load_dotenv` —— 单行解析失败仅记日志、不抛异常(代码:`utils/env.py:8-29`)。
- 统一日志改由 `utils/logging.py:get_logger`,支持 `LOG_LEVEL` 与 `LOG_DIR`,写入控制台 + `logs/app.log`。
- 抑制 `dotenv` 与 `dotenv.main` logger 至 ERROR,避免 `.env` 单行错误污染输出(`utils/logging.py:48-50`)。

这是项目第一次对**进程入口可靠性**做的横向治理。

### 3.2 异步化与超时治理(2026-02-24, `4365c0b`)

`/content/illustrate` 改为 `async def` + `asyncio.wait_for`,超时阈值由 `configs/content_generation.yaml` 的 `illustration.api_timeout` 提供,触发返回 504。代码:`api/main.py:209-257`。

后续 `/agent/img_extractor`(`df6c96e`)沿用同一异步入口风格,确立"长耗时 IO 必须可配置超时"的统一约束(已写入 `.claude/rules/architecture-constraints.md` 第 4.3 节)。

### 3.3 性能与体验优化

| 日期 | 提交 | 优化点 |
|---|---|---|
| 2026-02-22 | `574201e` | TTS 长文案分段并发请求 + 音频流拼接(突破单次 300 字硬限) |
| 2026-02-22 | `2f69682` | OCR 配置化插图截取,避免每次重新检测 |
| 2026-02-24 | `4365c0b` | 插图接口异步化,避免阻塞 worker |
| 2026-03-11 | `9e7556a` | 图片 URL 拉取支持重定向与 HTTP 回退,降低外网失败率 |
| 2026-03-11 | `ebc634b` | 分镜检测稳健性与多布局支持(自适应 2x3、3x2 等) |

### 3.4 安全加固

- **`c9e6620`(2026-03-30)**:`.gitignore` 增补 `configs` 下 AccessKey 类 CSV,防止误提交密钥。
- **`bdf2cb6`(2026-02-26)**:Aliyun TTS 显式使用 certifi CA,修复 TLS 验证问题。
- **`fd9fbcf`(2026-03-11)**:漫画分格输出目录 `_chown_recursive` 修正属主为 `www:www`,与生产部署的最小权限一致(`api/main.py:294-335`)。
- **`b049775`/`b6bf2f6`(2026-02-07)**:测试默认 mock 外部 API,凭据缺失也能跑(`tests/test_api_ocr.py:33-55`),避免 CI 因密钥缺失失败。

无 CVE 级修复记录;**安全约束更多通过架构约束体现**(配置/密钥与代码分离、容错加载、最小权限)。

---

## 四、重构优化阶段

项目目前显式 `refactor` 标签的提交只有 1 条,但**架构性收紧**散见于多个 `feat`/`chore`:

### 4.1 显式 refactor

- **`b2c8a9c`(2026-02-28)refactor(illustrate)**:`/content/illustrate` 接口入参收敛为 `illustration_prompts + interests`,其余从 yaml 读取。这是项目至今唯一一次主动**API 入参面缩小**重构,确立了"入参只承载业务变量,运行参数走配置"的边界。

### 4.2 隐式架构调整(以 chore/feat 形式落地)

- **2026-02-08 `c0c2506`**:进程入口治理(safe_load_dotenv、统一 logger),改变了所有模块的 `.env` 加载与日志获取方式。
- **2026-02-22 `2f69682`**:OCR 流水线显式拆为 `preprocessing/` → `service.py` → `postprocessing/question_parser.py`,首次落地"流水线三段式"(后写入 `.claude/rules/architecture-constraints.md` 第 2.3 节)。
- **2026-03-30 `e02bc42`**:`.cursorrules` 扩充——把"模块化、禁止巨型单体、改动后更新 architecture/progress"写进项目级强制规则,首次将隐性约定显性化。
- **2026-03-31 `53defda` feat(marketing) + `85ce215` docs(project)**:营销发布主路径从"开放平台 API"切换到 "xiaohongshu-mcp",`README.md`、`memory-bank/4-progress.md`、`marketing/XHS_MCP_PUBLISH.md` 同步更新;旧 `client.py`/`xhs_api.yaml` 保留为可选遗留。这是项目至今规模最大的**主路径切换**。

### 4.3 代码质量提升

| 维度 | 落地证据 |
|---|---|
| 类型注解 | `api/schemas.py` 全 Pydantic、`ocr/service.py` 公共函数全签名 |
| 日志结构化 | `extra={...}` 普及(见 `api/main.py:81-86`、`ocr/service.py:194/258`) |
| 容错加载 | `_load_config` 模式在 `ocr/service.py`、`voice_synthesis/aliyun_tts.py`、`content_generation/story_generator/generator.py` 一致复用 |
| 测试覆盖 | `tests/` 13 个测试文件,覆盖单元、接口、e2e、漫画分格、签名等多场景 |
| 文档与代码同步 | `9022ba7` 后建立 `memory-bank/`,所有重要决策在 `5-decision-log.md` 留痕 |

---

## 五、当前状态与未来方向

### 5.1 当前状态(截至 2026-05-04)

**已交付能力**:

- 7 个对外路由全部稳定:`/health`、`/ocr/recognize`、`/content/generate`、`/content/solution-guide`、`/voice/synthesize`、`/content/illustrate`、`/agent/img_extractor`(代码:`api/main.py`)。
- OCR 三引擎可选(`baidu`/`paddle`/`qwen_vl`),自动降级:`ocr/service.py:201-217`。
- 内容生成 4 段式故事(开头-发展-高潮-结尾),300–500 字,与插图分镜对齐:`content_generation/story_generator/generator.py:113-131`。
- 插图生成:多 Provider(TTAPI/Midjourney + Gemini),兴趣驱动角色,异步 + 可配置超时。
- 营销自动化:小程序介绍 + 每日视频两种模式,默认走本地 `xiaohongshu-mcp` 自动发帖。
- 长期记忆库 6 份文档持续维护;`.cursorrules` + `.claude/rules/`(本次新增的 code-style、workflow、architecture-constraints)三件套就位。

**当前工作焦点**(`memory-bank/4-progress.md` 2026-04-01):

> `daily-video` 模式从 `uploads/vedio/<id>/info.md` 拼「本期视频信息」时:**过滤流水线/技术元数据**(时间、目录、工作流 ID、下载状态、文件名、URL 等),并尽量从 JSON 中抽取题目/学科/主题/剧情摘要;LLM 润色时同样只基于过滤后的教学相关材料。

工作流仍是单分支(`master`)、单作者(`fengwch`),所有提交协作者为 Cursor agent —— 与"AI 辅助 + 人工评审"的开发模式一致。

### 5.2 未来方向(从待办与决策推导)

#### 5.2.1 来自 `memory-bank/2-implementation-plan.md` 的未完成项

- [ ] **(可选遗留)开放平台发帖**:具备资质后在 `xhs_api.yaml` 填 `publish_note.method` 并使用 `--execute`。

#### 5.2.2 从近期改动趋势看可预见方向

| 方向 | 依据 |
|---|---|
| **更多内容生产源** | Coze 工作流接入(`5dbeb14`)+ 每日定时(`fe6ca4b`)已铺路;后续可能扩展 Coze 之外的低代码平台或自研编排 |
| **更多发布渠道** | 当前只有小红书;`marketing/` 目录命名与 `XHS_MCP_PUBLISH.md` / `XHS_OPEN_PLATFORM.md` 双文档结构暗示其他平台(抖音、视频号)可同样接入 |
| **OCR 引擎评测与默认切换** | `OCR_ENGINE` 三选一仍以 `baidu` 为默认;Qwen-VL 与 PaddleOCR 的实测表现可能推动默认值变更 |
| **故事 + 插图一体化交付** | `panels_per_prompt` / `panels_in_image` / `include_dialogue` 配置已就位(`content_generation/story_generator/generator.py:88-91`),后续可能把"故事 → 多格连环画 + 配音"做成端到端单接口 |
| **生产部署形态固化** | `gunicorn.conf.py` + `_chown_recursive` 已露出生产形态雏形;`scripts/install_on_server.sh` 与 `build_package.sh` 暗示"打包 + 部署到自有服务器"将持续完善 |
| **观测性增强** | 当前为本地 `logs/app.log` + 中间件耗时日志;若上量,需要外部 APM 与告警(目前未见相关提交) |

#### 5.2.3 已识别但未行动的风险

- **测试外部依赖凭据**:虽然默认 mock,但 `test_e2e_homework_flow.py` 真实链路依赖 `DASHSCOPE_API_KEY` 等;CI 化时需要凭据托管方案。
- **小红书 MCP 容器登录态**:依赖人工扫码登录与 cookie 持久化(`tools/xiaohongshu-mcp/README.md`),长期运行的 cookie 失效是已知运维风险。
- **配置项分散**:`configs/`(服务级)与 `config/`(业务级)双目录易混;新人易把营销配置放错位置(架构约束 §6 已显式禁止互迁)。

---

## 附录:阶段提交统计

| 阶段 | 时间窗 | 提交数 | 主要类型 |
|---|---|---|---|
| 启动 | 2026-02-06 ~ 02-08 | 12 | feat × 7、chore × 3、docs × 1、fix × 1 |
| 第一波内容能力 | 2026-02-22 | 5 | feat × 4、chore × 1 |
| 插图深化 | 2026-02-24 ~ 02-28 | 7 | feat × 4、refactor × 1、fix × 1、chore × 1 |
| 漫画分格 | 2026-03-10 ~ 03-11 | 5 | feat × 3、chore × 1、fix × 1 |
| Coze 接入 | 2026-03-27 | 1 | feat × 1 |
| 营销与记忆库 | 2026-03-30 ~ 03-31 | 11 | feat × 3、chore × 5、docs × 2、fix × 1 |
| **合计** | **2026-02-06 ~ 03-31** | **41** | feat × 22(54%)、chore × 11(27%)、docs × 4、fix × 3、refactor × 1 |

`feat` 占比 54% 体现项目仍在能力扩张期;`refactor` 仅 1 条且发生在能力快速堆叠后(`b2c8a9c`),与早期项目典型节奏吻合。
