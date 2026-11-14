# 智趣作业辅导 App — MVP 与第一阶段实施 SOP（DRAFT）

- **版本**：DRAFT v0.1
- **覆盖范围**：MVP + 第一阶段
- **目标读者**：单人 + AI 协作者
- **文档形式**：流程章节为主 + 任务清单为附录（混合型）

---

## 0. 引言：怎么使用本 SOP

> _本节定位：让任何接管者（人或 AI）在 5 分钟内知道这份文档是什么、不是什么、以及打开它的正确姿势。_

### 0.1 这份文档是什么

> _写作意图：明确"项目实施 SOP"的覆盖边界 —— 落实代码、功能、上线相关的工作流，不重写战略、产品、设计文档。_

这份文档是一份 **执行指南**，把 `docs/` 下已有的产品 / 技术决策落地为"可执行步骤 + 验收标准"。它关注的是"怎么做、谁来做、做到什么程度算完"，而不是"为什么做、做什么功能"。

在单人 + AI 协作场景下，这份文档还充当实操守则：每次改动先查对应章节，确认范围和验收标准，再动手。

### 0.2 这份文档不是什么

> _写作意图：避免新成员/AI 把它当成万能手册，明确边界。_

这份文档 **不替代** 任何战略、产品或规范文档：

- 战略与愿景看 `docs/项目章程.md`；功能定义与优先级看 `docs/产品需求文档.md`；系统设计看 `docs/技术架构文档.md`。
- 代码风格、目录边界、proto 工作流等开发细节在各子项目的 `CLAUDE.md` 与 `agent/.claude/rules/*.md` 中，本 SOP 只引用，不复制。
- 具体的代码风格细节（缩进、命名、docstring 格式）按需引用 `code-style.md`，不在这里重复收录。

### 0.3 子项目快速索引

| 子项目 | 路径 | 职责 | 主要语言 | 主要文档 |
|---|---|---|---|---|
| Agent | `agent/` | AI 原子能力（OCR / 故事 / 解题 / TTS / 插图 / 营销） | Python + FastAPI | `agent/CLAUDE.md` |
| Backend | `backend/` | 业务中枢（鉴权 / 作业 / 内容 / 订阅） | Go + Kratos v2 | `backend/CLAUDE.md` |
| App | `app/frontend/` | 跨端客户端（H5 / 小程序 / iOS / Android / HarmonyOS） | uni-app x + Vue 3 + TS | `app/CLAUDE.md` |

### 0.4 阅读顺序建议

- **第一次接管**：0 → 1 → 附录 A → 4 → 2。先用第 0 章定位文档用途，第 1 章了解当前状态，附录 A 看 P0 任务清单，第 4 章知道质量底线，第 2 章按阶段执行。
- **单点改动**：直接跳对应章节（如改订阅 → 2.5；改报告 → 3.4 + 附录 B.1）。
- **出问题**：跳到第 5 章（风险登记 + 应急 Playbook），定位责任域并止损，然后回第 4 章补质量门槛。
- **AI 协作时**：AI 接到任务后先读第 3.3 章"通用流程模板"，按 7 步顺序执行。

---

## 1. 现状盘点

> _本章定位：固定一个时间快照,让"未完成"的范围显式且可追溯。每条状态都附带责任子项目与佐证文件路径。_

### 1.1 已完成

> _写作意图：避免无效重复劳动 —— 列出"已经能跑且通过验收"的能力,后续工作在此之上叠加,不回炒。_

以下能力已经完成或接近完成，后续工作在此之上叠加，**不回炒已实现且通过验收的逻辑**：

- **agent**：7 个 HTTP 路由全部就位（OCR、内容生成、解题引导、语音、插图、漫画分格、健康检查），接口契约稳定。佐证：`agent/api/main.py`。
- **backend**：5 个核心 service 接通（Auth、User、Child、Assignment、Content），proto-first 流程已跑通（`make api && make wire` 可正常生成）。佐证：`backend/api/` 下 5 个 proto 文件 + `internal/server/http.go`。
- **app**：所有 P0 页面壳已搭建（登录、首页、作业拍照、报告、个人中心、订阅、奖励、安全）。佐证：`app/frontend/pages/` 目录。
- **文档**：项目章程、PRD、核心功能规格、技术架构、API 集成约定均已落库。
- **内部规范**：`agent/.claude/rules/*` 五份硬约束已定稿；`backend/CLAUDE.md` + `backend/memory-bank/` 已建立；`app/CLAUDE.md` + `app/.cursorrules` 已建立。

### 1.2 部分完成（有逻辑但有缺口）

> _写作意图：标记出"看起来已实现但实际缺关键链路"的项,这是上线前最易翻车的部分。_

以下能力看起来"已实现"，但实际缺少关键链路。**上线前必须逐一补齐**：

- **`agent/content/solution-guide`**：缺 `DASHSCOPE_API_KEY` 时静默回退到硬编码 mock，生产环境会输出假内容。见 `agent/content_generation/solution_generator/generator.py:69-76, 90-96`。**修复**：改为 503 响应，不返回 mock。
- **`backend/UpdateSubscription`**：handler 与 proto 已生成，但内部没有真实的微信/支付宝下单逻辑，仅返回成功 stub。**修复**：接入支付沙箱 + 订单表。
- **`app/pages/profile/security.uvue`**：页面已渲染，所有按钮 toast"功能开发中"。**修复**：实现修改密码 / 注销账户真实流程。
- **`app/pages/subscription.uvue`**：UI 完整，无对应 `api/subscription.ts`，无法发起请求。**修复**：新建 API 模块 + store。

### 1.3 未实现（白纸,需新建）

> _写作意图：清晰列出"代码层面完全没有对应实现"的能力,避免误以为只差封装。_

以下能力在代码层面**完全没有对应实现**，需要从零新建。不要误以为只差封装或配置：

- **backend**：
  - 周报/月报 endpoint（`report.proto` 未建）
  - 通知设置（开关 + 时段 + 渠道）endpoint（`notification.proto` 未建）
  - 无线打印调度（`print.proto` 未建）
  - 积分/徽章/排行榜（`reward.proto` 未建）
  - 相似题推荐 endpoint（`recommend.proto` 未建）
  - 内容偏好设置（兴趣 / 风格）endpoint（`preference.proto` 未建）
- **app**：
  - 缺失的 API 模块 —— `api/notification.ts`、`api/print.ts`、`api/reward.ts`、`api/subscription.ts`、`api/report.ts`、`api/preference.ts`
  - 周报/月报聚合 UI（单次报告页有，聚合页无）

上述能力属于第一阶段（P1）范围，**不得在 MVP 上线前启动**。

### 1.4 已知技术债务

> _写作意图：这些"能跑但留坑"的项必须显式记录,避免后期忘记。_

以下能力"能跑但留坑"，开发阶段可容忍，但必须在第一阶段期间逐一清理：

- **端到端测试依赖真实凭据**（`tests/test_e2e_homework_flow.py`），CI 暂无凭据托管。当前默认 mock 绕过了这条用例。**影响**：真实链路集成问题只在人工跑时才能发现。**清理时机**：MVP 上线前至少跑一次。
- **xiaohongshu-mcp 容器 Cookie 持久化依赖人工扫码**。Cookie 过期后需重新登录，无自动告警。**清理时机**：营销持续运行时。
- **配置目录双轨制**（`agent/configs/` vs `agent/config/`）。配置易放错位置。**清理时机**：第一阶段文档清理阶段。
- **营销 `client.py` / `xhs_api.yaml` 是遗留路径**，无活跃调用方。**清理时机**：决策日志中明确废弃或删除。
- **观测性局限于本地 `logs/app.log`**，无外部 APM。DAU < 1K 时可容忍。**清理时机**：DAU > 1K 或第一阶段上线前。

> 详细任务级清单见 **附录 A**（P0/MVP）和 **附录 B**（P1/第一阶段）。

---

## 2. MVP 上线流程（0–6 个月,P0 范围）

> _本章定位：把"从现状到 MVP 上线"的工作拆成可串行/可并行的步骤,每步给出"开始条件 → 操作 → 验收 → 产出"。_

### 2.1 MVP 的可上线定义（Definition of Done）

> _写作意图：用一句话回答"什么叫 MVP 做完了",作为后续每一步的验收锚。_

MVP 的上线定义（Definition of Done）由以下五个条件组成，必须同时满足：

1. **核心闭环可跑通**：用户能完成"注册 → 添加儿童档案 → 拍作业 → 看 OCR 题目 → 听故事 → 看解题引导 → 完成"全流程，且无 mock 数据（所有 AI 能力由真实 LLM / OCR 引擎输出）。
2. **订阅付费可走通**（沙箱级别即可）：用户能看到订阅选项、发起支付、收到回执。不要求真金白银，但要求完整回调链路可验证。
3. **三端可装/可访问**：iOS（TestFlight 或打包 IPA）、Android（APK 可安装）、微信小程序（预览模式或体验版）三端至少有一种方式能让测试用户实际使用。
4. **健康检查 + 中间件日志正常**：`/health` 路由全部返回 200，中间件 `duration_ms` 日志正常输出，无 N+1 或全阻塞调用。
5. **关键路径有测试覆盖**：每条 API 至少 1 条接口测试 + 关键流程至少 1 条 e2e 测试（可 mock 第三方）+ 核心逻辑至少 1 条单元测试。

### 2.2 阶段划分

| 阶段 | 时长 | 关键里程碑 |
|---|---|---|
| 2.2.1 准备期 | 第 0–1 月 | 凭据、基础设施、本地能跑 |
| 2.2.2 核心闭环期 | 第 1–3 月 | 拍作业 → 故事 → 解题 全链路通 |
| 2.2.3 商业化期 | 第 3–4 月 | 订阅支付 + 个人中心补全 |
| 2.2.4 上线准备期 | 第 4–5 月 | 性能、合规、内测 |
| 2.2.5 上线期 | 第 5–6 月 | 灰度 → 全量,监控就位 |

### 2.3 准备期（第 0–1 月）

> _写作意图：上线前的"前置条件"清单,避免后期发现凭据/环境问题倒退几周。_

准备期是 MVP 上线的前置条件清单。不完成这些，后续阶段会因环境问题倒退。

#### 凭据与基础设施

| 凭据/资源 | 用途 | 存放位置 | 验证方式 |
|---|---|---|---|
| `DASHSCOPE_API_KEY` | agent LLM + OCR + 故事生成 | `agent/.env` | `agent/` 启动 + `pytest` 通过 |
| `ALIYUN_TTS_*` | 语音合成 | `agent/.env` | `/voice/synthesize` 返回 base64 |
| `BAIDU_OCR_*` | 百度 OCR 引擎 | `agent/.env` | `/ocr/recognize` 返回结构化题目 |
| 微信支付商户号 + 证书 | 订阅支付 | `backend/configs/config.yaml` + 环境变量 | 沙箱下单 → 回调走通 |
| Apple Developer 证书 | iOS 打包 + IAP | 本地 Keychain | TestFlight 可安装 |
| 微信小程序 AppID + AppSecret | 微信登录 + 支付 | `backend/configs/config.yaml` | `wechat-login` 返回 token |
| `VITE_API_BASE_URL` | 前端 API 地址 | `app/frontend/.env` | app H5 可请求 backend |

#### 环境验证清单

- [ ] **agent**：启动期校验关键凭据（`DASHSCOPE_API_KEY`、选中的 OCR 引擎对应 key），缺失则 fail-fast 退出，不再静默 mock。
- [ ] **backend**：MySQL（`127.0.0.1:3307`）+ Redis（`127.0.0.1:6379`）通过 `docker compose up -d` 跑通。`make run` 启动后 `GET /health` 返回 200。
- [ ] **app**：HBuilderX 工程能在 H5（浏览器）+ 微信开发者工具下分别跑起来。H5 模式下能请求到 backend。
- [ ] **三端调用链**：app → backend（`:8000`）→ agent（`:8001`）。验证方式：app 提交一次作业拍照，backend 返回 OCR 结果 + 故事内容。

### 2.4 核心闭环期（第 1–3 月）

> _写作意图：MVP 真正的"产品价值"集中在这里 —— 拍作业到故事的串联体验。_

核心闭环期是 MVP 真正的"产品价值"集中交付阶段。目标是在 3 个月内让用户体验到"拍作业 → 看故事 → 听讲解"的完整流程。

#### 按子项目的关键任务

- **agent**：
  - 固化 OCR + 内容生成 + 解题引导链路，删除 silently-mock 的兜底（特别是 `generator.py:69-76` 的假数据回退）。
  - 解题引导缺 key 时返回 503，不返回 mock 故事。
  - 每条对外路由至少 1 条接口测试（正常路径 + 异常路径各一条）。

- **backend**：
  - `AssignmentService`：完成作业上传、OCR 调度（通过 `internal/pkg/aiagent`）、内容生成代理、报告写库。
  - `ContentService`：错误透传 + 超时 504（agent 504 → backend 504 → app 友好提示）。
  - 所有对 `agent/` 的调用走 `aiagent` 客户端，不裸拼 HTTP。
  - JWT refresh token 流程端到端验证：token 过期能自动续期。

- **app**：
  - 拍照/上传/进度/详情页对接真实 backend 接口。
  - 401 自动 refresh + 全局拦截器（`api/http.ts` 已有 401 处理，需补 refresh 重试逻辑）。
  - 单次作业报告页对接真实数据（OCR 结果 + 故事 + 解题引导），包含空态和异常态展示。

- **跨子项目**：
  - 数据契约对齐：backend 返回 `{ code: 0, message: "ok", data: {...} }`，agent 通过 backend 转换。
  - 字段命名：前端 TypeScript 接口声明 snake_case + camelCase 双形态，不擅自统一。
  - 错误码：app 端按 backend 的 `code` 区间做分类展示（40000 级别显示参数错误，30000 级别跳转登录等）。

### 2.5 商业化期（第 3–4 月）

> _写作意图：付费通路是 MVP 的核心 KPI（1000 付费用户),不能晚于核心闭环就绪。_

付费通路是 MVP 的核心 KPI（1000 付费用户），不能晚于核心闭环就绪。

- **backend `UpdateSubscription`**：接入微信支付沙箱（`mch_id` + `api_key` + 回调验签）和 Apple IAP 沙箱（`receipt` 验证 + `status` 校验）。订单表（`payment_orders`）设计包含：`user_id`、`plan`、`status`、`created_at`、`callback_data`。回调验签必须幂等（同一 `order_id` 的重复回调不重复激活订阅）。
- **app `subscription.uvue`**：新建 `api/subscription.ts`，在页面中 import 展示订阅选项、发起支付、展示回执。与 `stores/user.ts` 的订阅状态联动。
- **法务对齐**：用户协议、隐私政策（特别是儿童信息脱敏与处理条款）、自动续费提示（iOS 要求在订阅页明确标注"24 小时扣款"）。这些内容需在 app 端页面和 Apple 审核说明中同时体现。
- **测试**：沙箱下完整付费流程的 e2e（不刷真卡）。验证路径：发起 → 沙箱支付成功 → 回调验签通过 → 订阅状态变为 active → 用户可见。

### 2.6 上线准备期（第 4–5 月）

> _写作意图：从"能用"到"敢上线"之间的工程化补齐。_

从"能用"到"敢上线"之间，需要补齐以下工程化合规项：

- **性能**：拍照到首张故事可视化的 P95 ≤ 30s（PRD 验收标准）。以 backend 中间件 `duration_ms` 日志为准，采样 100 次请求验证。若超时，排查瓶颈优先在 agent LLM 调用链路（`agent/content_generation/`）和 backend → agent 的 HTTP 超时设置（当前 600s 太长，MVP 期可降为 120s）。
- **隐私合规**：
  - 儿童信息脱敏（昵称可展示但不入库明文身份证/手机号）。
  - 家长同意流程（首次注册时弹出隐私政策，勾选同意后方可使用）。
  - 注销账户能力（`app/pages/profile/security.uvue` 实现注销，backend 清理关联数据）。
- **上架材料**：
  - iOS：App Privacy 清单（数据收集类型、用途）、截图、描述。
  - Android：权限说明（存储、相机、位置），Google Play / 国内渠道各自要求不同。
  - 微信小程序：服务类目（教育 > 作业辅导）、隐私协议、服务器域名配置。
- **内测**：招募 5–10 个家庭跑 1 周，收集崩溃日志（app 端 `uni.onError` + backend 错误日志）和体验反馈。
- **内测修复**：P0/P1 缺陷必须在上线前修完，P2 入第一阶段队列。

### 2.7 上线期（第 5–6 月）

> _写作意图：从内测到全量的灰度路径,以及监控就位时点。_

从内测到全量的灰度路径。单人 + AI 场景下没有自动灰度平台，灰度通过以下手动方式实现：

- **灰度节奏**：5%（内部 + 亲友 1–2 人）→ 20%（种子用户 10–20 人）→ 50%（半量）→ 100%。每级至少观察 3 天再推进下一级。
- **灰度控制方式**：
  - app 端：通过 `VITE_API_BASE_URL` 指向不同环境（灰度环境连接独立的 backend 实例）。
  - backend：通过 JWT 中的 `user_id` 判断是否在灰度名单中（名单存储在 Redis SET `graylist:mvp`），灰度用户走新流程，非灰度用户走旧流程或展示"敬请期待"。
- **关键指标看板**：
  - DAU（日活用户数）
  - 付费转化率（注册用户中完成付费的比例）
  - 7 日留存（注册后第 7 天仍活跃的用户比例）
  - 健康检查成功率（`/health` 200 占比）
  - API 错误率（status ≥ 500 占比）
  - 核心链路 P95 耗时
- **客服与反馈通道**：公众号客服消息、邮件（`support@gameyeah.net`）、小红书评论回复、app 内反馈入口。所有反馈统一记录到文档或 issue 中，P0 当天修，P1 本周内修，P2 入下一阶段队列。
- **MVP 复盘**：第 6 月末做一次全面复盘，输出数据（用户量、留存、付费转化、崩溃率、Top 反馈）输入到第一阶段规划。复盘结果写入 `memory-bank/5-decision-log.md`。

### 2.8 切到第一阶段的判定

> _写作意图：避免还没站稳就摊大饼。_

进入第三章（第一阶段扩展）前，必须同时满足以下三个条件。任一条件未达标，都必须在 MVP 范围内继续修补，而非开启新能力。

1. **商业验证**：1000 付费用户达标，或 7 日留存率 ≥ 30%（取其一）。若留存达标但付费未达标，说明产品价值被认可但变现路径需调优，优先优化订阅页与支付流程，而非扩功能。
2. **稳定性**：主流程（拍作业 → OCR → 故事 → 解题引导）崩溃率 ≤ 0.5%。此指标以 app 端上报 + backend 健康检查日志为准，连续 7 天达标方可判定。
3. **迭代节奏**：团队（即使是单人 + AI）能维持连续 4 周的稳定迭代，每周至少完成 1 个 P0 修复或优化，无超过 3 天的阻塞项。

若未达标，回到 2.2–2.7 对应阶段补齐，并在 `memory-bank/5-decision-log.md` 记录延迟原因与下一步计划。

---

## 3. 第一阶段扩展流程（6–12 个月,P1 范围）

> _本章定位：MVP 上线后,如何稳健引入"周报 / 通知 / 打印 / 奖励 / 推荐 / 偏好"等扩展能力。_

### 3.1 引入的硬约束（不可违反）

> _写作意图：所有新增改动都必须先读完这些规则文件,直接引用而不复制。_

参考文件：
- `agent/.claude/rules/code-style.md`
- `agent/.claude/rules/development-workflow.md`
- `agent/.claude/rules/architecture-constraints.md`
- `agent/.claude/rules/project-takeover-guide.md`
- 根 `CLAUDE.md` + 各子项目 `CLAUDE.md`

### 3.2 P1 能力的优先级排序

> _写作意图：单人 + AI 容量有限,必须有顺序,不能"什么火就做什么"。_

以下六项按优先级从高到低排列，单人 + AI 场景下必须逐项完成，**不允许并行启动超过两项**，避免全部烂尾：

1. **学习报告 v2（周报/月报）** —— 用户黏性核心 → 后端 `report.proto` + app 报表页
2. **通知与提醒** —— 提升留存 → 后端 notification + app `api/notification.ts`
3. **奖励体系（积分/徽章/排行榜）** —— 儿童动机驱动 → `reward.proto` + app reward 页接 API
4. **相似题推荐** —— 学习深度 → 后端 endpoint,agent 复用现有内容生成
5. **无线打印调度** —— 家长便利 → `print.proto` + 第三方打印对接
6. **内容偏好设置** —— 个性化优化 → 后端偏好表 + app 偏好页

### 3.3 每一项的通用流程模板

> _写作意图：把第一阶段每个 P1 任务都压成同一个套路,避免每次都现想。_

通用步骤：
1. **proto 先行**（仅 backend）—— 写 `.proto`,跑 `make api && make wire`
2. **biz / data 实现** —— usecase 先,GORM model 后,单测先于实现（TDD)
3. **handler 接通** —— `internal/service/*.go` 调用 usecase
4. **agent 联动**（如需）—— 在 `agent/<module>/` 下加新 service 入口,严守"AI 服务层不碰持久化"
5. **app 对接** —— 新建 `api/<feature>.ts`,在 page 中 import,补单测
6. **联调** —— 三端真实环境跑一次完整流程
7. **文档同步** —— 更新对应 `CLAUDE.md` + `memory-bank/`(如有)

### 3.4 单项任务的详细步骤参考附录 B

> _写作意图：流程模板 + 附录任务表 = 完整指南。详细任务/验收/文件路径见附录 B。_

---

## 4. 协作与质量门槛(适用全周期)

> _本章定位：单人 + AI 协作的纪律,以"提交 / 审查 / 测试 / 文档"四个门槛把质量锁住。_

### 4.1 提交规范

> _写作意图：保证 git 历史可读,Conventional Commits 是硬约束。_

参考：
- `agent/.claude/rules/development-workflow.md` 第 2 章
- 根 `CLAUDE.md` "Branch & Commit Convention"

关键要点：
- `type(scope): subject` 格式,scope 与子项目目录对齐
- 一个 commit 只做一件事
- 不要 `--no-verify`,不要 amend 已推送提交
- AI 协作时 footer 加 `Co-Authored-By: Claude <noreply@anthropic.com>`

### 4.2 自我审查(单人场景下的 PR-style review)

> _写作意图：没有他人审查时,自己用 PR diff 视角再读一遍 —— 单人 + AI 也要有这道闸。_

每次提交前，按以下清单过一遍 diff（可在 `git diff --cached` 输出上逐项核对）：

1. **接口契约破坏没？** —— 新增/修改的 proto 字段是否与 `openapi.yaml` 同步？`backend/` 的响应 `{code, message, data}` 结构有没有被改？`app/` 的 TypeScript 接口是否对齐？
2. **有没有硬编码？** —— 密钥、路径、第三方 endpoint 是否全部来自配置或环境变量？新增 env 是否同步 `.env.example`？
3. **日志够不够？** —— 关键流程节点（开始/完成/降级/异常）是否有 info/warning/error 级日志？是否带 `WithContext(ctx)` 和结构化字段？异常是否带 traceback？
4. **测试够不够？** —— 被改动的 usecase 是否有单元测试？新增路由是否有接口测试？关键链路是否有 e2e 或至少一条集成测试？mock 边界是否合理？
5. **文档同步没？** —— 改 agent 路由 → `agent/CLAUDE.md` + `agent/memory-bank/3-architecture.md`；改 backend proto → `backend/CLAUDE.md` + `backend/memory-bank/`；改 app 页面 → `app/CLAUDE.md` + `app/.cursorrules`；跨子项目 → 根 `CLAUDE.md`。

**AI 协作时的分工**：AI 负责生成代码与测试草稿，人负责 review。AI 不应直接执行 `git commit` 或 `git push`；人在 review 后确认再提交。

**架构/契约类改动的前置动作**：在写代码前，先在对应子项目的 `memory-bank/5-decision-log.md` 写一条决策记录（问题 / 选项 / 决策 / 原因），然后引用该决策编号到 commit message 或 PR 描述。

### 4.3 测试要求

> _写作意图：测试不通过禁止合并;测试不依赖凭据可跑。_

参考:
- `agent/.claude/rules/development-workflow.md` 第 4 章

关键要点:
- 单元测试覆盖纯逻辑,接口测试覆盖每个对外路由,e2e 覆盖关键链路
- mock 边界放在项目自有 service 入口,不 mock 第三方 SDK 内部
- 修复 Bug 必须先写一条能复现 Bug 的失败测试再提交修复

### 4.4 文档同步

> _写作意图:对外契约 / 架构 / 决策类改动必须同步文档,否则 SOP 会自我过期。_

文档同步是"提交前自检清单"的最后一项。不同改动类型对应不同的文档责任矩阵：

| 改动类型 | 必须更新的文档 | 可选更新 |
|---|---|---|
| 新增/修改 agent HTTP 路由 | `agent/CLAUDE.md`（路由列表） | `agent/memory-bank/3-architecture.md` |
| 新增/修改 backend proto | `backend/CLAUDE.md`（服务列表） | `backend/memory-bank/3-architecture.md` |
| 新增 backend 错误码区段 | `backend/memory-bank/3-architecture.md`（错误码表） | — |
| 架构/契约/技术选型决策 | 对应子项目 `memory-bank/5-decision-log.md` | — |
| 改 app 页面路由或组件模式 | `app/CLAUDE.md` | `app/.cursorrules` |
| 改跨子项目数据契约 | 根 `CLAUDE.md` + 双方子项目 `CLAUDE.md` | `docs/api/*` |
| 改本 SOP 适用范围或流程 | 本文件 + `memory-bank/5-decision-log.md`（记"为何调整"） | — |

**执行方式**：不要在 PR 里只写"同步了文档"，要在 PR 描述中列出改动的具体文件路径与行号范围。审查者验证：文档与代码是否一致、是否有遗漏项。

**防过期机制**：每季度（或每完成一个里程碑）做一次文档审查，以 `git log` + 文件实际状态为准，把过时的内容删掉或更新。审查结果写入 `memory-bank/4-progress.md`。

### 4.5 配置与密钥

> _写作意图:杜绝硬编码,密钥泄漏即吊销。_

参考:
- `agent/.claude/rules/code-style.md` 第 8 章
- `agent/.claude/rules/architecture-constraints.md` 第 6 章

关键要点:
- 一切密钥走环境变量
- 新增 env 同步 `.env.example`
- 进程入口加载一次,业务模块禁止再加载

---

## 5. 风险登记与应急

> _本章定位:把"明知道会出问题"的点提前登记,出事时有 playbook 可循。_

### 5.1 风险登记

> _写作意图:每条风险都有"触发信号 / 影响面 / 应对动作 / 责任人"。_

| 风险 | 触发信号 | 影响面 | 应对动作 |
|---|---|---|---|
| LLM 凭据失效 | 调用 401/403、503 飙升 | 解题引导、故事生成全失效 | 切备用 key + 手机告警 |
| OCR 引擎不稳 | 错误率 > 5% | 拍作业入口失效 | 切第二引擎(baidu→qwen_vl) |
| 微信/Apple 支付沙箱挂 | 订阅 e2e 失败 | 商业化阻塞 | 暂停灰度,排查回调 |
| xiaohongshu-mcp Cookie 过期 | 自动发帖 401 | 营销停摆 | 容器重新扫码登录 |
| 数据库连接池打满 | API 504 飙升 | 全部业务受影响 | 重启 backend + 调连接池 |
| 上架被拒 | 应用商店审核失败 | 上线延期 | 按反馈整改 + 备用渠道(H5) |

### 5.2 应急 Playbook

> _写作意图:线上出事的前 30 分钟脚本,避免临时翻文档。_

#### 第 0–5 分钟：定位

1. **看健康检查**：`GET /health`（backend `:8000`）和 `GET /health`（agent `:8001`）。哪个返回非 200，责任域就在哪一层。
2. **看中间件耗时日志**：backend `internal/server/http.go` 的日志带 `method/path/status/duration_ms`。若某一类路由集体变慢，可能是下游 agent 阻塞或数据库连接池打满。
3. **看错误码分布**：`50000–59999` 区间飙升 = 外部依赖问题（agent / WeChat / SMS）；`10000–19999` 飙升 = 基础设施问题（MySQL / Redis / 磁盘）。

#### 第 5–15 分钟：止损

1. **回滚优先**：若最近 2 小时内有部署，先 `make run` 上一个稳定版本（或直接用上一个 `dist/*.tar.gz` 包）。回滚后确认 `/health` 恢复。
2. **切流量 / 切 Provider**：
   - agent OCR 引擎故障 → 在 `agent/configs/ocr_config.yaml` 切到备用引擎（`baidu` → `qwen_vl` 或 `paddle`），重启 agent。
   - agent 插图生成故障 → `content_generation.yaml` 中切 Provider（TTAPI → Gemini），重启 agent。
   - backend 某 service 异常 → 若 gRPC 层可用，临时在 `internal/server/http.go` 中屏蔽该路由（不推荐，除非无回滚包）。
3. **降级，不造假**：
   - 解题引导挂 → 临时关闭入口（前端 toast "解题引导暂时不可用"），**不要**返回 mock 数据。
   - TTS 挂 → 回退到纯文本展示，保留故事内容。
   - 插图挂 → 返回已生成的故事 + 占位图，不阻断阅读。

#### 第 15–30 分钟：通知与记录

1. 在 `memory-bank/5-decision-log.md` 开一条 incident 记录（问题 / 触发信号 / 止损动作 / 待排查点），24 小时内补完根因分析。
2. 若涉及用户数据或支付，优先在决策日志中标记影响面（受影响用户数、时段、是否涉及资金）。
3. 复盘会议（即使是单人）在 48 小时内完成，输出改进项并写入 `2-implementation-plan.md` 或 `4-progress.md`。

### 5.3 监控就位时点

> _写作意图:不是上线后才补监控,而是和功能同步。_

监控能力与业务阶段绑定，不允许"先上线后补监控"。

#### MVP 上线前必须就位（≤ 1K DAU）

| 监控项 | 采集方式 | 告警阈值参考 |
|---|---|---|
| 健康检查 | `GET /health` 轮询 | 连续 2 次非 200 |
| API 错误率 | 中间件日志中的 status ≥ 500 | > 1% 持续 5 分钟 |
| P95 请求耗时 | 中间件日志中的 `duration_ms` | P95 > 5000ms |
| 关键路径埋点 | 业务代码 info 级日志 | OCR → 内容生成 全链路超时 > 30s |

此阶段允许仅使用本地日志（`logs/app.log` + Zap 文件 rotation），但必须保证日志格式统一为 JSON，且包含 `trace_id`、`user_id`、`method`、`path`、`status`、`duration_ms` 等字段。

#### 第一阶段上线前必须就位（> 1K DAU 或预期快速增长）

- **外部 APM / Trace**：接入 Datadog / Sentry / 阿里云 ARMS 等，覆盖 backend 和 agent 的关键链路（trace 从 app 请求 → backend → agent → 外部 API）。
- **结构化日志聚合**：将 `logs/app.log` 通过 Filebeat / Fluentd 等采集到 ELK / Loki / SLS，支持按 `trace_id` 检索全链路。
- **告警通道**：从"看日志"升级到"微信/钉钉/邮件告警"，错误率和 P95 阈值下调至更严格水平。

#### 禁止项

- 不允许在 > 1K DAU 阶段仍只依赖本地文件日志排查问题。
- 不允许关键路径（拍作业 → OCR → 故事 → 解题引导）没有任何耗时埋点。

---

## 附录 A — P0 / MVP 任务清单

> _本附录定位:可勾选执行的"MVP 之前必须做完"的任务表。每行就是一个最小可工作单元(可一次 commit 完成)。_

> **列说明**:
> - **状态**:未实现 / 部分完成 / 已完成-待验收
> - **优先级**:P0(MVP 必须),其它优先级见附录 B
> - **关联文件**:相对仓库根目录路径

### A.1 Agent 子项目 P0 任务

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| agent | 解题引导 | 缺 `DASHSCOPE_API_KEY` 时移除静默 mock,改为 fail-fast | 部分完成 | 启动校验 + 503 响应 | 缺 key 启动报错,运行时返回 503 | `agent/content_generation/solution_generator/generator.py:69-76,90-96` | P0 |
| agent | 健康检查 | 健康检查覆盖关键依赖(OCR 引擎 / LLM) | 部分完成 | 增加依赖探活 | `/health` 返回各依赖状态 | `agent/api/main.py` | P0 |
| agent | OCR | 引擎降级开关(主引擎挂时自动切备) | 未实现 | 配置 + 实现 | 主引擎宕机时仍能识别 | `agent/ocr/`、`agent/configs/ocr.yaml` | P0 |
| agent | 配置 | 整理 `configs/` vs `config/` 双轨 | 部分完成 | 文档说明边界 + 运行验证 | 新人能在 README 直接判断放哪边 | `agent/configs/`, `agent/config/` | P0 |

### A.2 Backend 子项目 P0 任务

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| backend | 订阅 | `UpdateSubscription` 接入微信/Apple 支付沙箱 | 部分完成(存根) | proto 字段补全 + biz 实现 + 订单表 + 回调验签 | 沙箱下完整下单 → 回调 → 状态更新走通 | `internal/biz/usecase/subscription.go`, `api/subscription/v1/*` | P0 |
| backend | 订阅 | 订单幂等 + 重复回调防护 | 未实现 | 唯一约束 + 状态机 | 重复回调不重复扣款 | `internal/data/payment_order.go`(新建) | P0 |
| backend | 作业 | 上传 + OCR 调度 + 报告写库 全链路 | 部分完成 | 串通 agent 返回到 DB | app 拍照后能在报告页看见结果 | `internal/biz/usecase/assignment.go` | P0 |
| backend | 内容 | 内容生成代理(故事 + 解题引导)| 部分完成 | 错误透传 + 超时 504 | agent 504 → backend 504 → app 友好提示 | `internal/biz/usecase/content.go` | P0 |
| backend | 鉴权 | JWT refresh token 流程 | 部分完成 | 端到端验证 | token 过期能自动续期 | `internal/biz/usecase/auth.go` | P0 |
| backend | 中间件 | 请求耗时 / 状态码 / 用户 ID 结构化日志 | 部分完成 | 字段对齐 | 日志可被聚合查询 | `internal/server/http.go` | P0 |

### A.3 App 子项目 P0 任务

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| app | 订阅 | 新建 `api/subscription.ts` + 接 `subscription.uvue` | 部分完成(无 API) | API 模块 + store + 调用 | 列表/升级/支付回执可视通 | `app/frontend/api/subscription.ts`(新建), `pages/profile/subscription.uvue` | P0 |
| app | 安全 | `pages/profile/security.uvue` 移除"功能开发中" | 部分完成 | 修改密码 / 注销账户实现 | 真实流程跑通 | `app/frontend/pages/profile/security.uvue` | P0 |
| app | 拍作业 | 拍照 → 上传 → 进度 → 结果展示 闭环 | 部分完成 | 与 backend 对齐错误码与超时提示 | iOS / 微信小程序 双端可走通 | `pages/homework/*`, `api/assignment.ts` | P0 |
| app | 报告 | 单次作业报告页对接真实数据 | 部分完成 | 字段映射 + 空态/异常态 | 包含 OCR 结果 + 故事 + 解题引导 | `pages/report/detail.uvue` | P0 |
| app | 鉴权 | 401 自动 refresh + 全局拦截 | 部分完成 | 拦截器 + 重试 | token 过期用户无感知续期 | `app/frontend/api/http.ts`, `stores/user.ts` | P0 |
| app | 跨端 | H5 + 微信小程序 + iOS 三端冒烟 | 未完成 | 编译 + 真机/模拟器测 | 三端核心闭环都跑通 | 全工程 | P0 |

### A.4 跨子项目 P0 任务

| 范围 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|
| 跨子项目 | 三端契约文档对齐(响应包格式 / 错误码) | 部分完成 | 全表 review | 一份文档即可定位每个 endpoint 形态 | `docs/api/AI-AGENT-INTEGRATION.md`, `docs/api/*` | P0 |
| 跨子项目 | `.env.example` 模板覆盖三个子项目 | 部分完成 | 整合一份 + 子项目链接 | 新人按模板填即可启动 | 各子项目 `.env.example` | P0 |
| 跨子项目 | 上架材料(iOS / Android / 微信小程序) | 未实现 | 隐私清单 + 类目 + 截图 | 三平台审核包齐全 | `docs/release/`(新建) | P0 |
| 跨子项目 | 上线灰度方案(5/20/50/100%) | 未实现 | 文档 + 配置 | 灰度键开关可用 | `docs/release/rollout.md`(新建) | P0 |

---

## 附录 B — P1 / 第一阶段任务清单

> _本附录定位:MVP 上线后逐个落地的 P1 能力清单,推荐按列出顺序执行。_

### B.1 学习报告 v2(周报 / 月报)

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| backend | 报表 | `report.proto` 设计(周报 / 月报) | 未实现 | proto 文件 + 生成 | `make api` 通过 | `api/report/v1/*`(新建) | P1 |
| backend | 报表 | usecase + 数据聚合(按周/月汇总作业) | 未实现 | biz 实现 + 单测 | 单测覆盖关键聚合分支 | `internal/biz/usecase/report.go`(新建) | P1 |
| backend | 报表 | handler 接通 | 未实现 | service 实现 | 接口测试通过 | `internal/service/report.go`(新建) | P1 |
| app | 报表 | `api/report.ts` + 周/月报页面 | 部分完成(单次报告页有,聚合页无) | API + 页面 | 三端可视 | `app/frontend/api/report.ts`, `pages/report/weekly.uvue`, `pages/report/monthly.uvue` | P1 |

### B.2 通知与提醒

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| backend | 通知 | 通知设置 endpoint(开关 + 时段 + 渠道) | 未实现 | proto + biz + handler + 表 | 接口测试通过 | `api/notification/v1/*`(新建) | P1 |
| backend | 通知 | 推送渠道接入(微信模板 / iOS APNs) | 未实现 | 适配层 + 配置 | 至少一个渠道走通 | `internal/data/notification/*`(新建) | P1 |
| app | 通知 | `api/notification.ts` + 设置页 | 未实现 | API + UI | 设置可保存可触发 | `app/frontend/api/notification.ts`(新建), `pages/profile/notification.uvue` | P1 |

### B.3 奖励体系(积分 / 徽章 / 排行榜)

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| backend | 奖励 | `reward.proto`(积分账户 + 徽章 + 排行榜) | 未实现 | proto 文件 | 生成通过 | `api/reward/v1/*`(新建) | P1 |
| backend | 奖励 | 积分变动事务 + 徽章规则引擎 | 未实现 | biz + 数据表 | 关键场景单测通过 | `internal/biz/usecase/reward.go`(新建) | P1 |
| backend | 奖励 | 排行榜计算(周榜 / 月榜) | 未实现 | 缓存 + 任务 | Redis 排行榜可读 | `internal/data/reward/*`(新建) | P1 |
| app | 奖励 | `api/reward.ts` + 奖励页接 API | 部分完成(页面壳) | API + 数据绑定 | 真实数据展示 | `app/frontend/api/reward.ts`(新建), `pages/reward/*` | P1 |

### B.4 相似题推荐

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| backend | 推荐 | 相似题 endpoint | 未实现 | proto + biz + 调度逻辑 | 接口测试通过 | `api/recommend/v1/*`(新建) | P1 |
| agent | 推荐 | 复用现有内容生成,新增 service 入口 | 未实现 | 入口函数 + 单测 | 单测通过 | `agent/content_generation/recommend/*`(新建) | P1 |
| app | 推荐 | "再来一题" 入口 + UI 展示 | 未实现 | 页面 + API 调用 | 三端可走通 | `pages/homework/recommend.uvue`(新建) | P1 |

### B.5 无线打印调度

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| backend | 打印 | `print.proto` + 任务调度 | 未实现 | proto + 第三方对接 | 至少一个打印服务跑通 | `api/print/v1/*`(新建), `internal/biz/usecase/print.go`(新建) | P1 |
| app | 打印 | `api/print.ts` + 打印入口 | 未实现 | API + UI | 提交打印任务 → 状态查看 | `app/frontend/api/print.ts`(新建), `pages/print/*`(新建) | P1 |

### B.6 内容偏好设置

| 子项目 | 模块 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| backend | 偏好 | 偏好设置 endpoint(兴趣 / 风格) | 未实现 | proto + biz + 表 | 接口测试通过 | `api/preference/v1/*`(新建) | P1 |
| backend | 偏好 | 偏好接入到 agent 调用参数 | 未实现 | 调用链改造 | 偏好变化后生成内容随之变 | `internal/biz/usecase/content.go` | P1 |
| app | 偏好 | 偏好设置 UI + API | 部分完成(壳) | API + 提交 | 设置可保存可生效 | `app/frontend/api/preference.ts`(新建), `pages/profile/preference.uvue` | P1 |

### B.7 技术债务清理

| 范围 | 任务 | 当前状态 | 缺什么 | 验收标准 | 关联文件 | 优先级 |
|---|---|---|---|---|---|---|---|
| agent | e2e 测试凭据托管 | 未实现 | CI 凭据注入 | CI 默认跑非凭据用例,夜间跑 e2e | `tests/`, CI 配置 | P1 |
| agent | xiaohongshu-mcp Cookie 监控 | 未实现 | 探活脚本 + 告警 | Cookie 失效有提示 | `marketing/xiaohongshu/*` | P1 |
| 跨子项目 | 外部 APM 接入(若 DAU > 10K) | 未实现 | 选型 + 接入 | 关键链路有 trace | 全工程 | P1 |
| agent | 配置目录双轨制清理 | 未实现 | 决策日志 + 迁移 | 单一目录或文档明确边界 | `agent/configs/`, `agent/config/` | P1 |
| agent | 营销 `client.py` / `xhs_api.yaml` 处理 | 未实现 | 决策日志 + 删除/保留 | `decision-log` 标明 | `agent/marketing/xiaohongshu/client.py`, `agent/config/xhs_api.yaml` | P1 |


---

## 附录 C — 参考与索引

### C.1 项目内文档

- `docs/项目章程.md` — 战略、预算、时间盒
- `docs/产品需求文档.md` — PRD,P0/P1/P2 功能列表
- `docs/核心功能规格说明.md` — 核心模块详细规格
- `docs/技术架构文档.md` — 技术架构总图
- `docs/api/AI-AGENT-INTEGRATION.md` — agent ↔ backend 集成约定
- `docs/README.md` — 项目文档总目录

### C.2 子项目文档

- 根 `CLAUDE.md` — 跨子项目协作规则
- `agent/CLAUDE.md` — agent 子项目接管手册
- `backend/CLAUDE.md` — backend 子项目接管手册
- `app/CLAUDE.md` — app 子项目接管手册

### C.3 硬约束规则

- `agent/.claude/rules/code-style.md` — 代码风格
- `agent/.claude/rules/development-workflow.md` — 开发流程
- `agent/.claude/rules/architecture-constraints.md` — 架构约束
- `agent/.claude/rules/development-history.md` — 开发历史(背景)
- `agent/.claude/rules/project-takeover-guide.md` — 项目接管指南

### C.4 长期记忆库

- `agent/memory-bank/` (如有)
- `backend/memory-bank/` — 架构 / 决策日志
- 本 SOP 重大调整 → 写入对应 `memory-bank/5-decision-log.md`

### C.5 SOP 版本演化

| 版本 | 变更摘要 |
|---|---|
| DRAFT v0.1 | 首版,基于现状盘点 + PRD |
| DRAFT v0.2 | 填补全部"待写要点"占位符 |

---

## DRAFT 评审清单(供编辑时自检)

提交本 SOP 正式版前,确保:

- [ ] 每个章节的"写作意图"占位符替换为实际内容
- [ ] 附录 A/B 的状态列与代码现状再校对一次(以 `git log` 与文件实际状态为准)
- [ ] 跨章节内部链接(如"详见附录 B")没有断
- [ ] 风险登记的"责任人"列对单作者场景明确(都是 fengwch,但应急 playbook 的判断点要写清楚)
- [ ] 至少跑过 1 次目录树验证:附录关联文件路径都真实存在(或显式标了"新建")
- [ ] 大版本变更记录到 `memory-bank/5-decision-log.md`(若涉及对外契约)
