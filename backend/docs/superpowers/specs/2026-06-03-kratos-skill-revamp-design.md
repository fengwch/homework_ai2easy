# Kratos Custom Skill Revamp — Design

- **Date**: 2026-06-03
- **Author**: Claude (with user approval)
- **Scope**: `/Users/fengwanchang/.claude/skills/custom-kratos-project/SKILL.md` + two new helper scripts

## 1. Goal

把现有的 Kratos v2 skill 从"通用框架速记"升级为"事实对齐 + 硬约束 cookbook + 可复用脚本 + CI 钩子"。Skill 不绑定任何具体业务项目，但所有命令、目录、命名、约束都按 Kratos v2 实战约定表述清楚。


## 2. Non-Goals

- 不改造项目本身的 `.cursorrules`、`CLAUDE.md`、`memory-bank/`
- 不引入新的工具链（依然用 `protoc + protoc-gen-go + protoc-gen-go-grpc + protoc-gen-go-http + wire + kratos`）
- 不写大型代码生成器；只提供两个薄脚本与四个内联模板
- 不改 skill 名称 / description 之外的系统级元数据（`name: kratos-project` 保留）

## 3. Target Audience

- AI 协作者（Claude Code / Cursor）打开一个 Go + Kratos v2 项目时立即能用的导航
- 新加入的人类工程师快速了解"开发 → 验证 → 部署 → 排错"的完整链路
- 任何使用 proto-first + Wire DI + gRPC/HTTP 双协议暴露的项目

## 4. SKILL.md 重写后结构（17 节）

| # | 章节 | 性质 | 要点 |
|---|---|---|---|
| 1 | Overview | 改 | 适配 Go + Kratos v2 + 双协议 + proto-first + Wire DI；不绑定业务 |
| 2 | Quick Reference | 改 | 仅列实际 target：`init / api / tidy / wire / build / build-fast / test / test-unit / test-api / test-short / dev / run / pack / clean / all` |
| 3 | Tool Installation | 改 | 真实安装命令 + 系统级 protoc 提示 |
| 4 | Project Structure | 改 | 通用 Kratos v2 layout（`api/<domain>/v1/`、`internal/biz/{model,usecase}`、`internal/data/{dao,model,repository}`、`internal/pkg/*`、`internal/conf/`、`internal/server/`、`internal/service/grpc/<domain>_service.go`、`internal/testutil/`） |
| 5 | gRPC + HTTP Unified | 保留+补 | 禁手写 HTTP；编译期断言完整写法 |
| 6 | Proto File Requirements | 改 | 包名 `api.<domain>.v1`、`go_package` 形如 `<module>/api/<domain>/v1;v1`、service `<Domain>Service`、`<Action>Request/<Action>Reply`（**Reply 非 Response**）、字段带 `// 注释`、只 import `google/api/annotations.proto` |
| 7 | Code Generation Workflow | 改 | `make api` 同时生成 `conf.pb.go`；`make wire` 依赖 `make api`；`make clean` 会清掉所有生成代码 |
| 8 | Wire Dependency Graph | 新增 | provider 链 + 排错 cookbook（`wire: X not provided` / 循环依赖 / 缺 `make wire`） |
| 9 | Configuration & Secrets | 新增 | `make dev` vs `make run`；`conf.proto` 加字段流程；**通用铁律**：所有 secret 走环境变量 |
| 10 | Logging（pkg/logger） | 新增 | `*log.Helper` + `WithContext(ctx)`；`LoggerConfig` 字段清单；禁止 `fmt.Println` / `log.Println` / 自建 `zap.New*` |
| 11 | Error Codes | 新增 | 六段式（10000-19999 系统 / 20000-29999 业务 / 30000-39999 鉴权 / 40000-49999 参数 / 50000-59999 外部 / 60000+ 预留） |
| 12 | Testing | 改 | 三层：`make test-unit` / `make test-api` / `make test-short`；miniredis + FakeRepo；凭据型测试必须 `//go:build integration` |
| 13 | CI / Pre-commit Hooks | 新增 | pre-commit 跑 `make api && make wire && git diff --exit-code`；CI 必跑 `make test-unit` 与 `make build`；`make test-api` 走夜间 job |
| 14 | Troubleshooting | 改 | cookbook：protoc 缺失、wire 失败、proto 改完没 `make api`、CORS 没开、上游 502、生成代码失同步 |
| 15 | Reusable Scripts | 新增 | `scripts/new_service.sh`（一键起新 service 骨架） + `scripts/secret_audit.sh`（扫可疑明文） |
| 16 | Inline Templates | 新增 | proto RPC / service 编译期断言 / usecase 接口 / data repo 实现 四件套 |
| 17 | Related Resources | 改 | 引 Kratos / Wire / googleapis 官方 + 项目自身 `.cursorrules` / `CLAUDE.md`（如有） |


## 5. 关键事实修正（diff 概要）

| 旧 skill 错误 | 修正 |
|---|---|
| 列了 `make check-go / make lint` | 删除（项目没这俩 target） |
| 目录 `cmd/user/` 单 service 形态 | 改为通用 `cmd/<svc>/` |
| `Request/Response` 命名 | 改为 `Request/Reply`（与 Kratos 实战一致） |
| `make api` 只生成业务 proto | 补"同时生成 `internal/conf/conf.pb.go`" |
| 缺 `make clean` 副作用说明 | 补"会清掉所有生成代码" |
| 缺 secrets 管理章节 | 新增"所有 secret 走环境变量"通用铁律 |
| 缺日志与错误码章节 | 新增 `pkg/logger` 与六段式错误码 |
| 缺 wire 排错 | 新增 cookbook |
| 缺测试三层分级 | 新增 `test-unit` / `test-api` / `test-short` |
| 缺 CI / pre-commit 建议 | 新增 |

## 6. 新增脚本

### 6.1 `scripts/new_service.sh <service-name>`

- 输入小写 service 名（如 `payment`）
- 自动生成：
  - `api/<name>/v1/<name>.proto`（含一个示例 `Get` RPC）
  - `internal/biz/usecase/<name>_usecase.go`（构造函数 + 一个示例方法）
  - `internal/service/grpc/<name>_service.go`（含 `var _ v1.XxxServiceHTTPServer = ...` 编译期断言 + 一个示例实现）
- 末尾打印"下一步"清单（编辑 proto → `make api` → 注册 ProviderSet → `make wire` → 注册 HTTP → `make build`）
- **不**自动改 `provider.go` 与 `http.go`（避免误改已有代码）

### 6.2 `scripts/secret_audit.sh`

- 扫仓库 `*.go / *.yaml / *.yml / *.json / *.env / *.proto`
- 排除 `vendor / node_modules / .git / unipkg / dist / *.example / *.md`
- 模式：`app[_-]?secret` / `jwt[_-]?secret` / `password\s*[:=]` / `api[_-]?key` / `access[_-]?key` / `token\s*[:=]`
- 有命中 → 退出码 1，提示用户(a) 移到环境变量 (b) `.gitignore` (c) 改 `.example`
- 无命中 → 退出码 0

## 7. 成功标准

1. `SKILL.md` 重写后，**任何**与原 skill 描述冲突的项目实际现象都能在新 skill 找到正确做法
2. 在示例项目上执行 `scripts/new_service.sh foo` 能在 5 秒内起好 3 个文件（proto、usecase、service）、给出下一步清单
3. 在包含 `password: 123456` 的 `configs/config.yaml` 上执行 `scripts/secret_audit.sh` 能命中并退出非零
4. pre-commit / CI 钩子片段可被任意项目直接复制使用
5. 不出现任何具体项目名（如 `homework-ai2easy` / `smartstudy` / `app/frontend` 等）

## 8. 风险与回退

- **风险 A**：重写后 skill 变长，AI 上下文吃紧 → 已用 18 节精炼内容（每节短），最终体积预计 < 25KB
- **风险 B**：新脚本在不同 OS 行为差异 → 脚本只用 `bash` 通用语法（不依赖 GNU 特有 flag），用 `set -euo pipefail`
- **风险 C**：用户对某些章节命名/取舍有意见 → spec review 阶段你提出来我改；改动局部，不会重写整个 skill
- **回退**：原 SKILL.md 留 `SKILL.md.bak` 备份，写完新版后让用户验收；不通过则 `mv SKILL.md.bak SKILL.md`

## 9. 验收流程

1. 落地：写新 `SKILL.md` + 两个脚本 + `SKILL.md.bak`
2. 自检：跑 `scripts/secret_audit.sh` 确认脚本自身不误报
3. 用户验收：用户 review spec（如本文件）+ review 新 `SKILL.md` 实际内容
4. 通过：删除 `.bak`；失败：回滚
