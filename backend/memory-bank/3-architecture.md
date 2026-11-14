# 架构记录

## 顶层目录与职责

```
backend/
├── api/<domain>/v1/<domain>.proto   # 唯一接口契约源（HTTP + gRPC）
├── cmd/server/                      # 进程入口 + Wire 注入
├── configs/                         # YAML 配置（按环境分文件）
├── deploy/                          # 部署脚本与制品布局
├── docs/                            # 仓库内对外文档（API、运维）
├── fonts/                           # PDF 渲染所需字体
├── internal/
│   ├── biz/usecase/                 # 业务用例：依赖接口，组合多 repo
│   ├── conf/                        # Bootstrap proto + 生成代码
│   ├── data/                        # 仓储实现：MySQL/Redis/AI Agent
│   ├── pkg/                         # 共享工具（aiagent/jwt/logger/sms/...）
│   ├── server/                      # HTTP & gRPC Server 装配 + 中间件
│   ├── service/grpc/                # proto 生成接口的实现，做薄适配
│   └── testutil/                    # miniredis、Fake Repo 等测试工具
├── openapi.yaml                     # make api 自动生成
├── scripts/                         # 一次性运维脚本
├── test/                            # 集成 / API 测试
├── third_party/                     # 引入的 proto 依赖（google/api 等）
└── uploads/                         # 静态文件挂载点
```

## 请求生命周期

```
client (HTTP/gRPC)
   ↓
internal/server          注入中间件 (Recovery / CORS / JWT / MultipartDecoder)
   ↓
internal/service/grpc    实现 v1.<Service>HTTPServer 接口（薄适配）
   ↓
internal/biz/usecase     业务用例，依赖接口
   ↓
internal/data            GORM / Redis / AI Agent 客户端的具体实现
```

## 关键模块约束

- **proto 优先**：每条 RPC 必须带 `google.api.http` 注解；新增/变更接口的流程是 *改 proto → `make api` → 实现 service*。**禁止**手写 HTTP handler，**禁止**删除 `var _ v1.XxxServiceHTTPServer = (*XxxService)(nil)` 这类编译期断言。
- **service/grpc 是适配层**：只做参数解析 / 调用 usecase / 错误映射，不写业务逻辑、不直接读写存储。
- **biz/usecase 只依赖接口**：`UserRepo`、`AuthRepo` 等接口在同包声明，`internal/data` 提供实现，Wire 注入。
- **internal/data 不向外泄露 GORM model**：模型保留在数据层，转换为业务结构后再交给 usecase。
- **internal/pkg/* 不向上依赖**：可以依赖 `internal/conf`，但禁止依赖 `biz` / `data` / `service` / `server`。
- **配置只走 conf.Bootstrap**：业务代码不要再读裸 YAML；新增字段必须先扩 `conf.proto`。

## 五大对外服务

| 服务 | proto | 主要 HTTP 路由 |
|---|---|---|
| AuthService | `api/auth/v1/auth.proto` | `/api/v1/auth/{send-sms, login, wechat-login, password-login, register, refresh, reset-password}` |
| UserService | `api/user/v1/user.proto` | `/api/v1/user/{profile, avatar, change-password, subscription}` |
| ChildService | `api/child/v1/child.proto` | `/api/v1/children/...` |
| AssignmentService | `api/assignment/v1/assignment.proto` | `/api/v1/assignments/{upload, scan, ...}` |
| ContentService | `api/content/v1/content.proto` | `/api/v1/content/...`，调用 `agent/` |

## 数据流

- **作业流**：客户端上传 → AssignmentService 持久化 → ContentService 调用 `agent/` OCR + 内容生成 → 结果写入并回包。
- **登录流**：手机号 / 微信 → AuthService 校验 → JWT 签发 → 后续请求经 `JWTAuthMiddleware` 注入 `ctx`。
- **AI 流**：所有对 `agent/` 的调用统一经 `internal/pkg/aiagent`，业务侧不直接拼 HTTP。

## 错误码区段

| 区间 | 类别 |
|---|---|
| 10000–19999 | 系统 / 基础设施 |
| 20000–29999 | 业务 |
| 30000–39999 | 鉴权 |
| 40000–49999 | 参数校验 |
| 50000–59999 | 外部依赖 |
| 60000+ | 预留 |

构造方式统一走 `internal/pkg/errors`，HTTP 层会自动映射状态码。

## 演进顺序

当现有架构无法承载新需求时，依次考虑：

1. 在既有 service 内扩展（加 RPC、加配置项）。
2. 拆分新子模块（在 `internal/biz/usecase` 增加用例 + 新建 repo 接口）。
3. 引入新顶层模块（如 `internal/job/`），先在决策日志登记。
4. 升级跨模块抽象（消息总线、外部任务队列），需要团队共识与决策记录。

不允许跳过这些步骤直接重写现有模块或大幅调整目录结构。
