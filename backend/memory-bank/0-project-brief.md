# 项目宪章

## 核心目标

本仓库为儿童作业辅导 App 的 **Go 主后端**（基于 Kratos v2），承担：

- 用户、儿童档案、作业 CRUD、订阅、奖励等业务领域。
- 鉴权（JWT + 短信验证码 + 微信小程序登录）、文件上传、PDF 导出。
- 编排 Python AI 服务层（`agent/`），将 OCR / 故事 / 解题引导 / 语音 / 插图能力对外整合。
- 为前端（uni-app x 客户端 `app/`）提供统一的 HTTP 接口；同时通过 gRPC 接受可信的内部调用。

## 范围

- **包含**：业务实体持久化（MySQL + Redis）、proto 优先的 HTTP/gRPC 接口、AI 服务调用代理、运维相关脚本与部署打包。
- **不包含**：
  - AI 算法实现（OCR / TTS / 故事生成等模型与 Prompt 工程在 `agent/` 仓库）。
  - 前端 UI（`app/`）。
  - 跨服务的复杂任务调度（如有需要先在决策日志登记）。
  - 微信支付、短信通道商服务对接细节（仅做抽象 + 替换 provider）。

## 与上下游的关系

- **下游**：`app/frontend` 通过 HTTP 调用本仓库；本仓库返回 `{ code, message, data }` 三段式响应。
- **上游**：`agent/` 通过 HTTP 提供 AI 能力，本仓库通过 `internal/pkg/aiagent` 客户端封装。
- **共享文档**：仓库根 `docs/` 是与前端、Agent 共享的 API 与设计契约源；本仓库的接口契约通过 `make api` 生成的 `openapi.yaml` 暴露。
