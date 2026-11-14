# 实施计划与里程碑

## 已交付（按业务领域）

- [x] **AuthService**：手机号验证码、密码、微信、注册、Token 刷新、密码重置共 7 个 RPC。
- [x] **UserService**：profile、avatar、change-password、subscription 4 个 RPC。
- [x] **ChildService**：儿童档案 CRUD（`/api/v1/children`）。
- [x] **AssignmentService**：作业上传、扫描、状态查询。
- [x] **ContentService**：调用 `agent/` 完成 OCR、故事、解题、TTS、插图等内容生成。
- [x] **基础设施**：Wire DI、proto 注解一体化 HTTP/gRPC、`pkg/logger` 全套结构化日志、错误码六段式分配、JWT 中间件、CORS、Swagger UI、`/uploads` 静态挂载。

## 待办 / 待评估

- [ ] **机密迁移**：当前 `configs/config.yaml` 中含微信 `app_secret`、JWT `secret` 等真实密钥，需要迁出至环境变量或外部秘钥管理。详见 `5-decision-log.md` 的相关条目。
- [ ] **凭据型集成测试隔离**：`test/` 目录下涉及真实第三方依赖的用例需要打 `integration` 标签或在 CI 中按需运行，避免默认 `make test` 受凭据缺失影响。
- [ ] **AI Agent 失败降级**：当前对 `agent/` 的调用缺少明确的熔断 / 降级策略；后续可在 `internal/pkg/aiagent` 加入超时分级与可选结果回退。
- [ ] **可观测性升级**：本地 Zap 日志 + `pkg/logger` 已经够用，但分布式 trace、指标、外部 APM 仍未接入。
- [ ] **WeChat MP 域名 / 协议合规**：`api_base_url` 默认指向 `https://hw.gameyeah.net`，前端在小程序后台需要保持一致；任何域名变更必须在前端 release notes 与决策日志中同步。

## 暂不计划

- 跨服务任务队列（消息中间件 / Worker 池）：当前业务体量不需要；如要做，先在决策日志登记并评估。
- GraphQL / WebSocket：与 Kratos / proto 一体化模式不一致，除非有强需求否则不引入。
- 前端 UI 直接连接 Python `agent/`：所有 AI 调用必须经由本仓库代理，保留鉴权与限流接口。
