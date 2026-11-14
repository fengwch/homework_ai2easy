# 智趣作业辅导 App — 未完成事项 SOP 手册

- **版本**：v1.0
- **覆盖范围**：MVP 上线前 P0 + 第一阶段 P1 + 技术债务
- **目标读者**：开发者 + AI 协作者
- **文档形式**：按主题/风险域分组，P0 详写、P1+ 速览

---

## 0. 如何使用本手册

### 0.1 文档定位

本手册是一份**执行指南**，将 `docs/` 下已有的产品/技术决策落地为"可执行步骤 + 验收标准"。它关注的是"怎么做、做到什么程度算完"，而不是"为什么做、做什么功能"。

**不是**：
- 不替代战略文档（`docs/项目章程.md`）
- 不替代产品文档（`docs/产品需求文档.md`）
- 不替代技术架构文档（`docs/技术架构文档.md`）
- 不替代各子项目的 `CLAUDE.md` 与 `memory-bank/`

### 0.2 子项目快速索引

| 子项目 | 路径 | 职责 | 主要语言 | 主要文档 |
|---|---|---|---|---|
| Agent | `agent/` | AI 原子能力（OCR / 故事 / 解题 / TTS / 插图 / 营销） | Python + FastAPI | `agent/CLAUDE.md` |
| Backend | `backend/` | 业务中枢（鉴权 / 作业 / 内容 / 订阅） | Go + Kratos v2 | `backend/CLAUDE.md` |
| App | `app/` | 跨端客户端（H5 / 小程序 / iOS / Android / HarmonyOS） | uni-app x + Vue 3 + TS | `app/CLAUDE.md` |

### 0.3 优先级定义

| 优先级 | 定义 | 执行时机 |
|---|---|---|
| **P0** | MVP 上线前必须完成，缺失则不可上线 | 当前立即执行 |
| **P1** | MVP 上线后、第一阶段内完成 | MVP 稳定后按序执行 |
| **P2** | 优化/改善类，可长期推进 | 资源富余时执行 |

### 0.4 阅读顺序建议

- **第一次接管**：0 → 1 → 第 2 章（安全与凭据）→ 第 3 章（核心链路）
- **单点改动**：直接跳对应主题章节
- **出问题**：跳第 10 章（风险登记与应急 Playbook）
- **AI 协作时**：先读本节定位，再跳对应 SOP 章节按步骤执行

---

## 1. 当前状态快照

### 1.1 已完成能力

- **agent**：7 个 HTTP 路由全部就位（OCR、内容生成、解题引导、语音、插图、漫画分格、健康检查），接口契约稳定。
- **backend**：5 个核心 service 接通（Auth、User、Child、Assignment、Content），proto-first 流程已跑通（`make api && make wire` 可正常生成）。
- **app**：所有 P0 页面壳已搭建（登录、首页、作业拍照、报告、个人中心、订阅、奖励、安全）。
- **文档**：项目章程、PRD、核心功能规格、技术架构、API 集成约定均已落库。
- **内部规范**：`agent/.claude/rules/*` 五份硬约束已定稿；`backend/CLAUDE.md` + `backend/memory-bank/` 已建立；`app/CLAUDE.md` + `app/.cursorrules` 已建立；根 `CLAUDE.md` 统一 monorepo 协作规则。

### 1.2 部分完成（有缺口）

以下能力"看起来已实现"，但缺少关键链路，上线前必须补齐：

- **`agent/content/solution-guide`**：缺 `DASHSCOPE_API_KEY` 时静默回退到硬编码 mock。**修复**：改为 503 响应，不返回 mock 数据。
- **`backend/UpdateSubscription`**：handler 与 proto 已生成，但内部无真实支付逻辑，仅返回成功 stub。**修复**：接入支付沙箱 + 订单表。
- **`app/pages/profile/security.uvue`**：页面已渲染，所有按钮 toast"功能开发中"。**修复**：实现修改密码 / 注销账户真实流程。
- **`app/pages/subscription.uvue`**：UI 完整，无对应 `api/subscription.ts`，无法发起请求。**修复**：新建 API 模块 + store。

### 1.3 未实现（白纸）

以下能力在代码层面完全没有对应实现，需要从零新建：

- **backend**：周报/月报 endpoint、通知设置、无线打印调度、积分/徽章/排行榜、相似题推荐、内容偏好设置。
- **app**：缺失的 API 模块 —— `api/notification.ts`、`api/print.ts`、`api/reward.ts`、`api/subscription.ts`、`api/report.ts`、`api/preference.ts`。

上述能力属于第一阶段（P1）范围，**不得在 MVP 上线前启动**。

### 1.4 已知技术债务

- **端到端测试依赖真实凭据**，CI 暂无凭据托管。清理时机：MVP 上线前至少跑一次。
- **xiaohongshu-mcp 容器 Cookie 持久化依赖人工扫码**。清理时机：营销持续运行时。
- **配置目录双轨制**（`agent/configs/` vs `agent/config/`）。清理时机：第一阶段文档清理阶段。
- **营销 `client.py` / `xhs_api.yaml` 是遗留路径**，无活跃调用方。
- **观测性局限于本地 `logs/app.log`**，无外部 APM。清理时机：DAU > 1K 或第一阶段上线前。

---

## 2. 安全与凭据

### 2.1 [P0] 机密从配置文件中迁出 → 环境变量

**背景**：`backend/configs/config.yaml` 中含微信 `app_secret`、JWT `secret`、数据库口令明文。`agent/` 的 `.env` 中亦含第三方 API key。这些凭据不应出现在版本控制的配置文件中。

**触发条件**：任何生产部署、CI/CD 构建、或向外部共享代码库前。

**前置依赖**：无。

**操作步骤**：

1. **backend 侧**：
   - 将 `backend/configs/config.yaml` 中的 `wechat.app_secret`、`jwt.secret`、数据库密码改为环境变量引用（Kratos config 支持 env 插值）。
   - 创建 `backend/.env.example`，列出所有需要的环境变量名（不含值）。
   - 将 `.env` 加入 `.gitignore`（若未加）。
   - 验证：`make dev` 在 `.env` 存在时正常启动；`.env` 缺失时报明确错误。

2. **agent 侧**：
   - 检查 `agent/.env` 是否已加入 `.gitignore`。
   - 确认 `agent/.env.example` 覆盖所有第三方 key 变量名。
   - 验证：启动期对缺失 key fail-fast（见 3.4 节），不再静默 mock。

3. **app 侧**：
   - 确认 `app/.env` / `app/.env.*` 已加入 `.gitignore`。
   - `VITE_API_BASE_URL` 保留在 `.env.example` 中。

4. **跨子项目**：
   - 在根 `.gitignore` 中确保 `**/.env`（不忽略 `.env.example`）。
   - 运行 `git ls-files | grep -i env` 确认无泄露。

**验收标准**：
- `git grep -i "sk-\|secret\|password\|api_key\|app_secret" -- '*.yaml' '*.yml' '*.toml'` 无真实值返回。
- `make dev` 在设置 `.env` 后正常启动。
- `.env.example` 文件中列出所有必需变量名。

**回退方案**：若环境变量方案在特定环境（如本地开发）不可行，可回退到 `config.dev.yaml` 中保留开发用密钥，但生产配置必须走环境变量。

**预估工作量**：M

---

### 2.2 [P0] 支付沙箱凭据接入（微信 + Apple IAP）

**背景**：`backend/UpdateSubscription` 仅有 stub 实现，无真实支付能力。MVP 商业化需要订阅支付通路。

**前置依赖**：微信支付商户号 + 证书、Apple Developer 证书。

**操作步骤**：

1. **订单表设计**：在 `internal/data` 中新建 `payment_orders` 表，字段包含 `user_id`、`plan`、`status`、`created_at`、`callback_data`、`order_id`（唯一约束）。
2. **微信支付沙箱**：在 `internal/pkg/wechat` 中接入微信支付 JSAPI 下单 + 回调验签逻辑。
3. **Apple IAP 沙箱**：在 `internal/data` 中实现 receipt 验证 + status 校验。
4. **回调幂等**：同一 `order_id` 的重复回调不重复激活订阅（唯一约束 + 状态机校验）。
5. **app 侧**：新建 `api/subscription.ts`，在 `subscription.uvue` 中对接展示订阅选项、发起支付、展示回执。

**验收标准**：沙箱下完整下单 → 回调 → 验签 → 订阅状态 active → 用户可见，全链路跑通。

**回退方案**：若沙箱凭据未就绪，可先用 mock 支付（仅内部测试），但不允许上线。

**预估工作量**：L

---

### 2.3 [P1] 凭据类条目速览

| 条目 | 所属主题 | 优先级 | 当前状态 | 一句话描述 | 关键文件 |
|---|---|---|---|---|---|
| e2e 测试凭据 CI 托管 | 安全与凭据 | P1 | 未实现 | CI 环境中注入第三方凭据以跑 e2e | `tests/`, CI 配置 |
| xiaohongshu-mcp Cookie 监控 | 安全与凭据 | P1 | 未实现 | Cookie 失效时自动告警提示 | `marketing/xiaohongshu/` |

---

## 3. 核心链路补齐

### 3.1 [P0] 作业上传 → OCR → 故事 → 解题 全链路打通

**背景**：目前 AssignmentService、ContentService、agent 路由各自就位，但三端串联尚未完整验证。

**前置依赖**：agent 凭据就绪（`DASHSCOPE_API_KEY` 等）、backend MySQL + Redis 在线、app H5 可请求 backend。

**操作步骤**：

1. **agent 侧**：确认 `/ocr/recognize`、`/content/generate`、`/content/solution-guide` 三端路由返回正确结构。删除 `generator.py` 中 silent-mock 兜底（见 3.4）。
2. **backend 侧**：
   - `AssignmentService`：完成作业上传 → 调用 `aiagent` OCR → 内容生成 → 结果写库。
   - `ContentService`：错误透传 + 超时 504。agent 504 → backend 504 → app 友好提示。
   - 所有对 `agent/` 的调用走 `internal/pkg/aiagent`，不裸拼 HTTP。
3. **app 侧**：
   - 拍照/上传/进度/详情页对接真实 backend 接口。
   - 单次作业报告页展示 OCR 结果 + 故事 + 解题引导，包含空态和异常态。
4. **联调**：三端真实环境跑一次完整流程。

**验收标准**：app 提交一次作业拍照 → backend 返回 OCR 结果 + 故事内容 + 解题引导，全链路无 mock。

**回退方案**：若 agent 端某能力临时不可用，按第 10 章 Playbook 执行降级（关闭入口 + toast 提示），不返回 mock 数据。

**预估工作量**：L

---

### 3.2 [P0] JWT refresh token 端到端验证

**背景**：JWT refresh 功能已有实现，但未验证 token 过期后自动续期的端到端流程。

**前置依赖**：backend HTTP 服务在线、app 端 `api/http.ts` 401 拦截器就位。

**操作步骤**：

1. **backend 侧**：验证 refresh 接口返回新的 access token + refresh token，旧 refresh token 失效。
2. **app 侧**：补全 `api/http.ts` 中 401 自动 refresh + 重试逻辑。原请求使用新 token 重新发送，对业务代码透明。
3. **测试**：模拟 token 过期 → 发起请求 → 自动 refresh → 原请求成功。

**验收标准**：token 过期后用户无感知续期，全流程不跳登录页。

**回退方案**：若 refresh 失败，正常跳登录页重新登录。

**预估工作量**：S

---

### 3.3 [P0] app 三端（H5/小程序/iOS）冒烟测试

**背景**：app 页面已搭建，需在 H5、微信小程序、iOS 三端分别验证核心流程可跑。

**前置依赖**：backend + agent 在线、HBuilderX 工程可编译。

**操作步骤**：

1. **H5**：HBuilderX → Run → H5 → 浏览器中验证登录、作业拍照、报告页。
2. **微信小程序**：微信开发者工具中导入编译 → 验证核心流程。注意 `urlCheck`、TLS 域名、服务类目。
3. **iOS**：HBuilderX → Run → iOS Simulator / 真机 → 验证核心流程。

**验收标准**：三端核心闭环（注册 → 添加儿童 → 拍作业 → 看报告）都跑通。

**回退方案**：若某端编译失败，优先排查 uni-app x 平台兼容性，回退到 H5 单端验证。

**预估工作量**：M

---

### 3.4 [P0] 解题引导缺 key 时静默 mock → 503 fail-fast

**背景**：`agent/content_generation/solution_generator/generator.py:69-76, 90-96` 中，缺 `DASHSCOPE_API_KEY` 时返回硬编码假内容。生产环境会输出假数据。

**前置依赖**：无。

**操作步骤**：

1. **agent 启动期**：校验关键凭据（`DASHSCOPE_API_KEY`），缺失则 fail-fast 退出，不再静默 mock。
2. **agent 运行时**：缺 key 的解题引导请求返回 503 + 明确错误 message。
3. **backend 侧**：将 agent 503 透传为业务错误码（50000 区间），app 显示友好提示。

**验收标准**：缺 key 启动报错，运行时返回 503，不返回任何 mock 数据。

**回退方案**：无。此修复为安全底线，不允许回退到 mock 行为。

**预估工作量**：S

---

## 4. 运维与可观测性

### 4.1 [P0] 健康检查 + 中间件结构化日志就位

**背景**：各服务 `/health` 路由存在但未覆盖关键依赖探活，中间件日志格式不统一。

**前置依赖**：无。

**操作步骤**：

1. **backend `/health`**：返回 MySQL 连接探活 + Redis ping + agent 可达性。任一依赖不可用返回降级状态（非 500，但标记 unhealthy）。
2. **agent `/health`**：返回 LLM key 有效 + OCR 引擎可达。
3. **中间件日志**：统一 JSON 格式，包含 `trace_id`、`user_id`、`method`、`path`、`status`、`duration_ms`。
4. **错误码分类**：确保 HTTP 层按 6 段式错误码区间正确映射。

**验收标准**：
- `GET /health` 返回各依赖状态。
- 请求日志可被 `jq` 聚合查询。
- 错误码区间与 `backend/memory-bank/3-architecture.md` 一致。

**回退方案**：无。此为基础设施底线。

**预估工作量**：S

---

### 4.2 [P0] AI Agent 失败降级策略

**背景**：当前 `agent/` 不可用会直接影响 ContentService 全部能力，无熔断/降级策略。

**触发条件**：`agent/` 响应超时、503、或连续 3 次请求失败。

**操作步骤**：

1. **backend `internal/pkg/aiagent` 侧**：
   - 超时分级：OCR 30s、故事 120s、解题 120s、插图 300s。
   - 连续失败 3 次后标记 agent 为 degraded，后续请求直接返回降级响应。
2. **降级策略**：
   - OCR 失败 → 提示"图片识别暂时不可用，请稍后重试"。
   - 故事生成失败 → 返回纯文本题目描述，不含故事。
   - 解题引导失败 → 关闭入口，toast "解题引导暂时不可用"。
   - 插图生成失败 → 使用占位图，不阻断阅读。
3. **app 侧**：按错误码区间做分类展示（50000 级别显示"服务暂时不可用"）。

**验收标准**：
- agent 不可用时，backend 不 hang、不返回 500，而是明确的降级响应。
- app 显示友好提示，不阻断用户其他操作。

**回退方案**：无。此策略为上线必需。

**预估工作量**：M

---

### 4.3 [P1] 运维类条目速览

| 条目 | 所属主题 | 优先级 | 当前状态 | 一句话描述 | 关键文件 |
|---|---|---|---|---|---|
| 外部 APM / Trace 接入 | 运维与可观测性 | P1 | 未实现 | DAU > 1K 后接入 Datadog / Sentry / ARMS | 全工程 |
| 结构化日志聚合 | 运维与可观测性 | P1 | 未实现 | `logs/app.log` → ELK / Loki，支持 trace_id 检索 | 全工程 |
| 告警通道升级 | 运维与可观测性 | P1 | 未实现 | 从"看日志"升级到微信/钉钉/邮件告警 | 全工程 |

---

## 5. 合规与上线

### 5.1 [P0] 儿童隐私合规

**背景**：应用面向儿童用户，必须满足家长同意、数据脱敏、账户注销等合规要求。

**操作步骤**：

1. **家长同意流程**：首次注册时弹出隐私政策，勾选同意后方可使用儿童相关功能。
2. **数据脱敏**：儿童昵称可展示，不入库明文身份证/手机号。
3. **账户注销**：`app/pages/profile/security.uvue` 实现注销功能，backend 清理关联数据（儿童档案、作业记录、学习报告）。
4. **隐私政策页面**：在 app 端和 Apple 审核说明中同时体现。

**验收标准**：
- 首次注册必须勾选隐私政策。
- 注销后关联数据被清理。
- Apple App Privacy 清单完整。

**回退方案**：无。此为合规底线。

**预估工作量**：M

---

### 5.2 [P0] 三平台上架材料

**前置依赖**：MVP 核心闭环已验证。

**操作步骤**：

1. **iOS**：App Privacy 清单（数据收集类型、用途）、截图、描述、Apple Developer 证书。
2. **Android**：权限说明（存储、相机）、国内渠道各自要求。
3. **微信小程序**：服务类目（教育 > 作业辅导）、隐私协议、服务器域名配置。

**验收标准**：三平台审核包齐全，可提交审核。

**预估工作量**：M

---

### 5.3 [P0] 上线灰度方案

**背景**：单人 + AI 场景下没有自动灰度平台，需要手动灰度方案。

**操作步骤**：

1. **灰度节奏**：5%（内部 1-2 人）→ 20%（种子用户 10-20 人）→ 50%（半量）→ 100%。每级至少观察 3 天。
2. **灰度控制**：
   - app 端：`VITE_API_BASE_URL` 指向不同环境。
   - backend：Redis SET `graylist:mvp` 控制灰度用户名单。
3. **关键指标**：DAU、付费转化率、7 日留存、健康检查成功率、API 错误率、核心链路 P95 耗时。

**验收标准**：灰度键开关可用，各灰度级别可独立观察。

**预估工作量**：S

---

### 5.4 [P1] 合规类条目速览

| 条目 | 所属主题 | 优先级 | 当前状态 | 一句话描述 | 关键文件 |
|---|---|---|---|---|---|
| WeChat MP 域名合规 | 合规与上线 | P1 | 需验证 | `api_base_url` 与小程序后台配置一致 | `backend/configs/config.yaml` |

---

## 6. 文档与知识管理

### 6.1 [P0] Phase 2/3 缺失文档清单

`docs/README.md` 列出了 7 大类 ~30+ 份文档。当前已交付 Phase 1（6 份）。以下是未交付的 Phase 2/3 文档：

| 类别 | 缺失文档 | 优先级 | 说明 |
|---|---|---|---|
| 开发计划 | 开发计划文档 | P1 | 任务分解、技术债务管理、版本控制策略 |
| 测试 | 测试策略与计划 | P1 | 功能/体验/性能/安全测试用例 |
| 测试 | 儿童测试专项计划 | P2 | 适龄性测试、内容安全测试 |
| 部署 | 部署与运维文档 | P1 | 部署架构、监控方案、备份策略 |
| 运营 | 用户手册 | P1 | 家长/儿童使用指南 |
| 运营 | 数据分析文档 | P2 | 关键指标定义、分析报告模板 |
| 合规 | 用户协议 | P1 | 法律合规 |
| 合规 | 隐私政策 | P1 | 儿童隐私特别条款 |
| 合规 | 内容安全审查文档 | P1 | AI 生成内容审查机制 |
| 安全 | 数据安全策略 | P1 | GDPR/COPPA 合规 |

### 6.2 [P0] 文档同步矩阵

| 改动类型 | 必须更新的文档 |
|---|---|
| 新增/修改 agent HTTP 路由 | `agent/CLAUDE.md` |
| 新增/修改 backend proto | `backend/CLAUDE.md` + `openapi.yaml` |
| 新增 backend 错误码区段 | `backend/memory-bank/3-architecture.md` |
| 架构/契约/技术选型决策 | 对应子项目 `memory-bank/5-decision-log.md` |
| 改 app 页面路由或组件模式 | `app/CLAUDE.md` |
| 改跨子项目数据契约 | 根 `CLAUDE.md` + 双方子项目 `CLAUDE.md` |
| 改本 SOP 适用范围或流程 | 本文件 + 对应 `memory-bank/5-decision-log.md` |

**执行方式**：在 PR 描述中列出改动的具体文件路径与行号范围。审查者验证文档与代码是否一致。

### 6.3 [P1] 文档类条目速览

| 条目 | 所属主题 | 优先级 | 当前状态 | 一句话描述 | 关键文件 |
|---|---|---|---|---|---|
| 文档防过期机制 | 文档与知识管理 | P1 | 未实现 | 每季度审查，以 `git log` + 文件实际状态为准 | 全 `docs/` |
| `docs/api/` 契约对齐 | 文档与知识管理 | P1 | 部分完成 | 全表 review 每个 endpoint 形态 | `docs/api/*` |

---

## 7. 代码债务与架构清理

### 7.1 [P0] agent 配置目录双轨制清理

**背景**：`agent/configs/` 与 `agent/config/` 并存，新人易放错位置。

**操作步骤**：

1. 审计两个目录下所有文件的被引用情况。
2. 确定唯一目录（建议 `agent/configs/`，与 backend 命名一致）。
3. 迁移文件、更新所有引用路径。
4. 在 `agent/CLAUDE.md` 中明确配置目录边界。

**验收标准**：单一配置目录，无歧义。

**预估工作量**：S

---

### 7.2 [P1] 代码债务类条目速览

| 条目 | 所属主题 | 优先级 | 当前状态 | 一句话描述 | 关键文件 |
|---|---|---|---|---|---|
| 营销 `client.py` / `xhs_api.yaml` | 代码债务 | P1 | 未处理 | 遗留路径无活跃调用方，需决策废弃或保留 | `agent/marketing/xiaohongshu/client.py` |
| 测试三层凭据隔离 | 代码债务 | P1 | 部分完成 | `test/` 中依赖真实凭据的用例需打标签 | `backend/test/` |
| 配置目录双轨制 | 代码债务 | P1 | 部分完成 | 见 7.1 节 | `agent/configs/`, `agent/config/` |

---

## 8. 第一阶段扩展（P1 能力）

### 8.1 优先级排序

| 序号 | 能力 | 一句话描述 | 预估工作量 |
|---|---|---|---|
| 1 | 学习报告 v2（周报/月报） | 用户黏性核心 | L |
| 2 | 通知与提醒 | 提升留存 | M |
| 3 | 奖励体系（积分/徽章/排行榜） | 儿童动机驱动 | L |
| 4 | 相似题推荐 | 学习深度 | M |
| 5 | 无线打印调度 | 家长便利 | M |
| 6 | 内容偏好设置 | 个性化优化 | M |

> 单人 + AI 场景下必须逐项完成，**不允许并行启动超过两项**。

### 8.2 通用流程模板

每项 P1 能力按以下步骤执行：

1. **proto 先行**（backend）—— 写 `.proto`，跑 `make api && make wire`
2. **biz / data 实现** —— usecase 先，GORM model 后，单测先于实现
3. **handler 接通** —— `internal/service/*.go` 调用 usecase
4. **agent 联动**（如需）—— 在 `agent/<module>/` 下加新 service 入口
5. **app 对接** —— 新建 `api/<feature>.ts`，在 page 中 import
6. **联调** —— 三端真实环境跑一次完整流程
7. **文档同步** —— 更新对应 `CLAUDE.md` + `memory-bank/`

### 8.3 P1 任务清单

| 能力 | 子项目 | 任务 | 关键文件 |
|---|---|---|---|
| 学习报告 v2 | backend | `report.proto` + usecase + handler | `api/report/v1/`, `internal/biz/usecase/report.go` |
| 学习报告 v2 | app | API + 周/月报页面 | `app/api/report.ts`, `pages/report/weekly.uvue` |
| 通知 | backend | notification proto + biz + 推送渠道 | `api/notification/v1/`, `internal/data/notification/` |
| 通知 | app | API + 设置页 | `app/api/notification.ts` |
| 奖励 | backend | reward proto + 积分事务 + 排行榜 | `api/reward/v1/`, `internal/biz/usecase/reward.go` |
| 奖励 | app | API + 奖励页 | `app/api/reward.ts`, `pages/reward/` |
| 推荐 | backend | recommend endpoint | `api/recommend/v1/` |
| 推荐 | agent | 复用内容生成，新增入口 | `agent/content_generation/recommend/` |
| 推荐 | app | "再来一题"入口 | `pages/homework/recommend.uvue` |
| 打印 | backend | print proto + 第三方对接 | `api/print/v1/` |
| 打印 | app | API + 打印入口 | `app/api/print.ts` |
| 偏好 | backend | preference proto + 接入 agent | `api/preference/v1/`, `internal/biz/usecase/content.go` |
| 偏好 | app | API + 设置 UI | `app/api/preference.ts` |

---

## 9. 质量门槛与协作纪律

### 9.1 提交规范

- `type(scope): subject` 格式，scope 与子项目目录对齐
- 一个 commit 只做一件事
- 不要 `--no-verify`，不要 amend 已推送提交
- AI 协作时 footer 加 `Co-Authored-By: Claude <noreply@anthropic.com>`

### 9.2 自我审查清单

每次提交前，按以下清单过一遍 diff：

1. **接口契约破坏没？** —— proto 字段与 `openapi.yaml` 同步？`{code, message, data}` 结构未改？TypeScript 接口对齐？
2. **有没有硬编码？** —— 密钥、路径、第三方 endpoint 是否全部来自配置或环境变量？
3. **日志够不够？** —— 关键流程节点有 info/warning/error 级日志？带 `WithContext(ctx)` 和结构化字段？
4. **测试够不够？** —— 被改动的 usecase 有单元测试？新增路由有接口测试？
5. **文档同步没？** —— 对应 `CLAUDE.md` + `memory-bank/` 已更新？

### 9.3 测试要求

- 单元测试覆盖纯逻辑，接口测试覆盖每个对外路由，e2e 覆盖关键链路
- mock 边界放在项目自有 service 入口，不 mock 第三方 SDK 内部
- 修复 Bug 必须先写一条能复现 Bug 的失败测试再提交修复

### 9.4 配置与密钥

- 一切密钥走环境变量
- 新增 env 同步 `.env.example`
- 进程入口加载一次，业务模块禁止再加载

---

## 10. 风险登记与应急 Playbook

### 10.1 风险登记表

| 风险 | 触发信号 | 影响面 | 应对动作 |
|---|---|---|---|
| LLM 凭据失效 | 调用 401/403、503 飙升 | 解题引导、故事生成全失效 | 切备用 key + 手机告警 |
| OCR 引擎不稳 | 错误率 > 5% | 拍作业入口失效 | 切第二引擎 |
| 微信/Apple 支付沙箱挂 | 订阅 e2e 失败 | 商业化阻塞 | 暂停灰度,排查回调 |
| xiaohongshu-mcp Cookie 过期 | 自动发帖 401 | 营销停摆 | 容器重新扫码登录 |
| 数据库连接池打满 | API 504 飙升 | 全部业务受影响 | 重启 backend + 调连接池 |
| 上架被拒 | 应用商店审核失败 | 上线延期 | 按反馈整改 + 备用渠道(H5) |

### 10.2 应急 Playbook

#### 第 0–5 分钟：定位

1. **看健康检查**：backend `:8000` 和 agent `:8001` 的 `/health`。哪个返回非 200，责任域就在哪一层。
2. **看中间件耗时日志**：`method/path/status/duration_ms`。若某一类路由集体变慢，可能是下游 agent 阻塞或数据库连接池打满。
3. **看错误码分布**：`50000–59999` 区间飙升 = 外部依赖问题；`10000–19999` 飙升 = 基础设施问题。

#### 第 5–15 分钟：止损

1. **回滚优先**：若最近有部署，先回退到上一个稳定版本。
2. **切 Provider**：
   - OCR 引擎故障 → 切备用引擎（`baidu` → `qwen_vl`），重启 agent。
   - 插图生成故障 → 切 Provider（TTAPI → Gemini），重启 agent。
3. **降级，不造假**：
   - 解题引导挂 → 关闭入口，**不要**返回 mock 数据。
   - TTS 挂 → 回退到纯文本展示。
   - 插图挂 → 占位图，不阻断阅读。

#### 第 15–30 分钟：通知与记录

1. 在 `memory-bank/5-decision-log.md` 开一条 incident 记录。
2. 若涉及用户数据或支付，标记影响面。
3. 48 小时内完成复盘，输出改进项写入 `memory-bank/4-progress.md`。

### 10.3 监控阈值速查

| 监控项 | 采集方式 | 告警阈值参考 |
|---|---|---|
| 健康检查 | `GET /health` 轮询 | 连续 2 次非 200 |
| API 错误率 | 中间件 status ≥ 500 | > 1% 持续 5 分钟 |
| P95 请求耗时 | 中间件 `duration_ms` | P95 > 5000ms |
| 关键路径 | 业务代码 info 级日志 | OCR → 内容生成全链路超时 > 30s |

**MVP 阶段**：本地日志（`logs/app.log`）+ JSON 格式统一即可。
**第一阶段**（DAU > 1K）：必须接入外部 APM + 日志聚合 + 告警通道。

---

## 附录 A — P0 任务清单（可勾选执行）

| 子项目 | 模块 | 任务 | 当前状态 | 验收标准 | 关键文件 |
|---|---|---|---|---|---|
| agent | 解题引导 | 移除静默 mock，改为 fail-fast | 部分完成 | 缺 key 启动报错，运行时返回 503 | `agent/content_generation/solution_generator/generator.py` |
| agent | 健康检查 | 覆盖关键依赖探活 | 部分完成 | `/health` 返回各依赖状态 | `agent/api/main.py` |
| agent | OCR | 引擎降级开关 | 未实现 | 主引擎宕机时仍能识别 | `agent/ocr/` |
| agent | 配置 | 整理双轨制 | 部分完成 | 单一配置目录 | `agent/configs/` |
| backend | 机密迁移 | 配置文件中密钥迁出 | 部分完成 | `git grep` 无真实值 | `backend/configs/config.yaml` |
| backend | 订阅 | 支付沙箱接入 | 部分完成 | 沙箱完整链路走通 | `internal/biz/usecase/` |
| backend | 作业 | 上传 → OCR → 报告全链路 | 部分完成 | 拍照后报告页有结果 | `internal/biz/usecase/assignment.go` |
| backend | 内容 | 错误透传 + 超时 504 | 部分完成 | agent 504 → app 友好提示 | `internal/biz/usecase/content.go` |
| backend | 鉴权 | JWT refresh 端到端验证 | 部分完成 | token 过期自动续期 | `internal/biz/usecase/auth.go` |
| backend | 日志 | 结构化日志字段对齐 | 部分完成 | 日志可聚合查询 | `internal/server/http.go` |
| app | 订阅 | API + 页面 | 部分完成 | 列表/升级/支付回执可视 | `app/api/subscription.ts` |
| app | 安全 | 移除"功能开发中" | 部分完成 | 修改密码/注销跑通 | `app/pages/profile/security.uvue` |
| app | 拍作业 | 拍照 → 上传 → 结果闭环 | 部分完成 | H5 + 小程序双端跑通 | `app/pages/homework/` |
| app | 报告 | 真实数据对接 | 部分完成 | 空态/异常态展示 | `app/pages/report/` |
| app | 鉴权 | 401 自动 refresh | 部分完成 | token 过期用户无感知 | `app/api/http.ts` |
| app | 跨端 | 三端冒烟 | 未完成 | H5 + 小程序 + iOS 核心闭环 | 全工程 |
| 跨子项目 | 契约 | 响应包格式 / 错误码对齐 | 部分完成 | 一份文档即可定位 | `docs/api/` |
| 跨子项目 | 凭据 | `.env.example` 全覆盖 | 部分完成 | 新人按模板填即可启动 | 各子项目 `.env.example` |
| 跨子项目 | 上架 | 三平台审核包 | 未实现 | iOS/Android/小程序材料齐全 | `docs/release/` |
| 跨子项目 | 灰度 | 灰度方案 | 未实现 | 灰度键开关可用 | `docs/release/rollout.md` |
| 跨子项目 | 合规 | 儿童隐私 | 未完成 | 家长同意 + 脱敏 + 注销 | 全工程 |

---

## 附录 B — P1 任务清单

见第 8 章"第一阶段扩展"中的任务表与技术债务速览表。

---

## 附录 C — 参考与索引

### 项目内文档

- `docs/项目章程.md` — 战略与目标
- `docs/产品需求文档.md` — PRD，P0/P1/P2 功能列表
- `docs/核心功能规格说明.md` — 核心模块详细规格
- `docs/技术架构文档.md` — 技术架构总图
- `docs/api/AI-AGENT-INTEGRATION.md` — agent ↔ backend 集成约定
- `docs/README.md` — 项目文档总目录

### 子项目文档

- 根 `CLAUDE.md` — 跨子项目协作规则
- `agent/CLAUDE.md` — agent 子项目手册
- `backend/CLAUDE.md` — backend 子项目手册
- `app/CLAUDE.md` — app 子项目手册

### 长期记忆库

- `agent/memory-bank/`
- `backend/memory-bank/`
- 本 SOP 重大调整 → 写入对应 `memory-bank/5-decision-log.md`

### SOP 版本演化

| 版本 | 变更摘要 |
|---|---|
| v1.0 | 正式版，按主题/风险域重组，清理人员与时间引用 |
