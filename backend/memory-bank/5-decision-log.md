# 关键决策日志

## 决策 #1：HTTP 与 gRPC 由同一份 proto 驱动

- **日期**：2026-02 项目奠基期（具体提交可在 `api/**/*.proto` 与 `internal/server/http.go` 历史中查到）。
- **问题**：是否手写 HTTP handler，或是用 Kratos 的 proto 注解机制。
- **决策**：**所有路由必须由 proto + `google.api.http` 注解驱动**，并在 `internal/service/grpc/*.go` 顶部用 `var _ v1.<Service>HTTPServer = (*<Service>)(nil)` 做编译期断言。`make api` 自动生成 `<svc>_http.pb.go`、`<svc>_grpc.pb.go`、`openapi.yaml`。
- **原因**：保证 HTTP / gRPC 一致；OpenAPI 与 RPC 客户端代码免维护；类型签名错配直接 build 失败。
- **影响**：禁止手写 HTTP handler；新增/修改 RPC 必须 *改 proto → make api → 实现 service*。

## 决策 #2：日志统一使用 `internal/pkg/logger`（Zap + lumberjack + Kratos 适配）

- **日期**：与上同期。
- **问题**：Kratos 默认 logger 与项目可观测性需求不匹配（缺 rotation、字段化、调用栈等）。
- **决策**：所有进程日志走 `internal/pkg/logger`，配置项落在 `LoggerConfig`（level / format / output / file_path / max_size / max_backups / max_age / compress / enable_caller / enable_stacktrace）。业务代码通过 Wire 注入 `*log.Helper`，使用前必须 `WithContext(ctx)`。
- **原因**：让 trace_id / 用户 id / 请求路径等结构化字段在所有层一致出现；文件 rotation 由配置决定，避免重复造轮子。
- **影响**：禁止 `fmt.Println`、`log.Println` 或自行 `zap.New*`；新增日志只能从注入的 helper 派生。

## 决策 #3：错误码六段式分配

- **日期**：与基础设施同期。
- **问题**：业务错误、鉴权错误、参数错误、外部依赖错误需要可识别区分。
- **决策**：错误码区段 10000–19999 系统、20000–29999 业务、30000–39999 鉴权、40000–49999 参数、50000–59999 外部依赖、60000+ 预留。`internal/pkg/errors` 提供构造函数与 HTTP 状态码映射。
- **原因**：客户端可在不读 message 的情况下做分类处理；监控可按区段告警。
- **影响**：新增错误必须落在合适区段，不可越界。

## 决策 #4：AI 调用经由 `internal/pkg/aiagent` 单点封装

- **日期**：项目接入 `agent/` 时。
- **问题**：是否允许业务代码直接拼 HTTP 调用 Python AI 服务。
- **决策**：所有对 `agent/` 的调用统一通过 `internal/pkg/aiagent` 客户端；业务用例只看到 Go 类型，对超时、重试、序列化无感。
- **原因**：未来若切换 AI Provider、加熔断、加 trace 注入只需要改一处。
- **影响**：新增 AI 能力时优先扩 `aiagent` 客户端，业务代码继续依赖接口；禁止业务用例引入 `net/http`、`io.Copy` 之类来调用上游。

## 决策 #5：`configs/config.yaml` 中机密暂留 — 待迁移至外部秘钥（待办）

- **日期**：2026-05-05 复盘记录。
- **问题**：当前 `configs/config.yaml` 内含微信 `app_secret`、JWT `secret`、数据库口令明文。
- **决策（暂行）**：开发阶段保持现状，但**不得**把这份 yaml 直接放进生产部署制品；生产环境必须用环境变量或外部秘钥管理服务覆盖。
- **生效条件**：仍在内网开发 / 个人开发者阶段。
- **回退条件**：上线生产前必须完成机密迁出，并在 `2-implementation-plan.md` 删除对应待办、在本日志补一条「迁移完成」决策。

## 决策 #6：测试三层 + 凭据隔离

- **日期**：测试基础设施搭建期。
- **问题**：单元、接口、集成层需要清晰区分；外部凭据缺失不应让默认 `make test` 失败。
- **决策**：
  - `internal/biz/usecase/*_test.go` 与 `internal/pkg/*_test.go` 走 `make test-unit`，依赖 `internal/testutil` 的 miniredis + Fake Repo，**不**依赖网络。
  - `test/` 目录是集成 / API 层，需要 MySQL + Redis 在线，由 `make test-api` 触发。
  - 任何依赖第三方真实凭据的用例必须显式标注；目前部分用例还没整理（见 `2-implementation-plan.md` 待办）。
- **原因**：CI 默认快速可跑；本地开发不被外部依赖卡住；真实凭据集中在受控环境。
- **影响**：新增测试时，先决定层级与是否依赖凭据，再决定放置目录与 mock 边界。
