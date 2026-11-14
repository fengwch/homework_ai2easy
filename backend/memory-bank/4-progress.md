# 进度记录

## 2026-05-05 — 文档基础设施补齐

- 新增 `backend/CLAUDE.md`：把 23 KB 的 `.cursorrules` 浓缩为 Claude Code 友好的导航式简版（模块边界、proto 工作流、错误码、运行命令、日志/配置规范）。
- 建立 `backend/memory-bank/` 六件套（本目录），与 `agent/memory-bank/` 对齐项目级长期上下文。
- 仓库根新增 `CLAUDE.md`，统一描述 monorepo（`agent/` + `app/` + `backend/` + `docs/`）的子项目边界与共享 docs 契约。

## 当前状态（2026-05-05）

- HTTP 8000 + gRPC 9002 双协议在线，依靠 proto 注解一体化，没有手写 handler。
- 5 大业务服务（Auth / User / Child / Assignment / Content）均已落地并接入 `agent/` AI 上游。
- 测试三层就位：`internal/biz/usecase/*_test.go`（单元）、`internal/pkg/*_test.go`（工具）、`test/`（集成 / API），由 `Makefile` 的 `test-unit` / `test-api` / `test-short` 区分调用。
- 部署形态：`make pack` 产出 `dist/<service>.tar.gz`（含 configs + scripts），具备生产环境一键部署雏形。

## 已识别风险

- **`configs/config.yaml` 中含真实密钥**：微信 `app_secret`、JWT `secret`、数据库口令均明文存在。生产部署前必须迁出至环境变量或外部秘钥服务。
- **AI Agent 单点依赖**：`agent/` 不可用会直接影响 ContentService 全部能力；目前没有熔断 / 降级策略。
- **凭据型集成测试**：默认 `make test` 会跑 `test/`，部分用例可能会因为缺凭据失败；待整理为可选标签。

## 接下来的潜在工作

- 把 `configs/config.yaml` 中的 `wechat.app_secret` / `jwt.secret` 改为只能从环境变量读取，并在 `.env.example` 中列示。
- 为 ContentService 调用 AI Agent 的关键路径补熔断 + 降级（例如：插图生成失败时退回纯文本）。
- 在 PR 流程中固化 `make api && make wire` 检查，避免 proto 与生成代码 / Wire 失同步。
