# 技术栈与外部依赖

## 强制选型

| 类别 | 选型 |
|---|---|
| 语言 | Go（与 `go.mod` 锁定的版本一致） |
| 框架 | Kratos v2.x |
| 接口定义 | Protocol Buffers + `google.api.http` 注解 |
| HTTP / gRPC 服务 | Kratos transport（同时启用，HTTP 由 proto 注解驱动） |
| 依赖注入 | Wire（`cmd/server/wire.go` → `wire_gen.go`） |
| ORM | GORM |
| 关系数据库 | MySQL（`smartstudy`） |
| 缓存 / 限流 / 验证码 | Redis |
| 鉴权 | JWT（`internal/pkg/jwt`），过期 30 天 |
| 日志 | Zap + lumberjack，封装为 Kratos `log.Logger` 适配（`internal/pkg/logger`） |
| 配置加载 | Kratos config（YAML → `Bootstrap` proto，环境变量覆盖） |
| API 文档 | OpenAPI（`make api` 自动生成 `openapi.yaml`，由 Swagger UI 在 `/q/swagger-ui` 提供） |
| 测试 | 标准 `testing` + `internal/testutil`（miniredis、Fake repo） |
| 部署 | `make pack` 打包 → `dist/<service>.tar.gz`（含 configs + scripts） |

## 外部服务

| 服务 | 用途 | 接入位置 |
|---|---|---|
| Python AI Agent | OCR / 故事 / 解题 / TTS / 插图 | `internal/pkg/aiagent` → `internal/data` |
| 阿里云短信 / Mock | 手机号验证码 | `internal/pkg/sms` |
| 微信小程序开放平台 | 微信一键登录 | `internal/pkg/wechat` |

## 端口与运行参数

- HTTP: `:8000`（`cmd/server/main.go` 默认） 
- gRPC: `:9002`（当前 `configs/config.yaml`；Kratos flag 默认是 `:9000`）
- AI Agent 上游：`http://0.0.0.0:8001`，超时 600s
- MySQL: `127.0.0.1:3307/smartstudy`
- Redis: `127.0.0.1:6379`

## 禁止使用

- 手写 HTTP handler（必须经由 proto 注解 + 生成代码）。
- 业务模块直接调用 `database/sql` 或裸 GORM；必须经过 `biz/usecase` 接口和 `internal/data` 实现。
- `fmt.Println` / `log.Println` 做事件日志；统一用 Wire 注入的 `*log.Helper`。
- 在代码中硬编码任何密钥、第三方 endpoint、用户路径。
- 引入与现有依赖功能重叠的库（再加一个日志库、再加一个 ORM）。
- 直接把第三方 SDK 数据结构暴露到对外契约；必须经过 proto schema 转换。
