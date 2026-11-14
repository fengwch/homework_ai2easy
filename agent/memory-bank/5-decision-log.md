# 关键决策日志

## 决策 #1：小红书业务 API 可配置

- **日期**：2026-03-28
- **问题**：社区「笔记发布」与电商 `common_controller` 的 method 名随开放平台产品线变化。
- **决策**：实现通用 `call_api(method, extra)` 与文档化 OAuth；`publish_note` 的 method 与 `extra_params` 由 `xhs_api.yaml` 配置，未配置时不发起虚构接口调用。

## 决策 #2：个人开发者以「仅生成软文」为主路径

- **日期**：2026-03-28
- **问题**：开放平台对「个人店铺」等开发者开通条件可能不满足自动发帖需求（见 [官方文档](https://open.xiaohongshu.com/document/developer/file/32) 等）。
- **决策**：文档与 README 明确默认流程为本地生成 + 手动发布；API 封装保留为可选，不强制配置 `XHS_*`。

## 决策 #3：自动发帖以 xiaohongshu-mcp 为主，不依赖开放平台发帖权限

- **日期**：2026-03-28
- **问题**：计划与文档曾以开放平台接口为自动发帖主路径，与个人开发者权限现实不符。
- **决策**：**正式发布**经 **xpzouying/xiaohongshu-mcp**（本仓库 `tools/xiaohongshu-mcp`，HTTP `/api/v1/publish` 或 MCP）；`client.py` / `xhs_api.yaml` 仅作可选遗留。说明文档：`marketing/XHS_MCP_PUBLISH.md`。
