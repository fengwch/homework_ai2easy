# 进度追踪

## 当前（2026-04-01）

- `daily-video` 模式从 `uploads/vedio/<id>/info.md` 拼「本期视频信息」时：**过滤流水线/技术元数据**（时间、目录、工作流 ID、下载状态、文件名、URL 等），并尽量从 JSON 中抽取题目/学科/主题/剧情摘要；LLM 润色时同样只基于过滤后的教学相关材料。

## 此前（2026-03-28）

- 已实现小红书软文 **主题配置 + 文案组装 + 合规检查 + 运营日记**；可选 **OAuth/签名客户端**（`marketing/xiaohongshu/client.py`，仅对接开放平台时用到）。
- **主推自动发帖**：**xiaohongshu-mcp**（Docker + 已登录 Cookie），经 `http://127.0.0.1:18060` 的 `/api/v1/publish` 或 MCP 发布；说明见 `marketing/XHS_MCP_PUBLISH.md`。
- **手动发帖**：运行 `scripts/xhs_publish.py`（不加 `--execute`），复制输出到 App。
- **可选（遗留）**：若有开放平台 `common_controller` 发帖资质，可配置 `XHS_*`、`xhs_api.yaml` 的 `publish_note.method` 并使用 `--execute`。

## 相关文件

- `marketing/xiaohongshu/publish_cli.py`
- `marketing/XHS_MCP_PUBLISH.md`
- `marketing/XHS_OPEN_PLATFORM.md`（开放平台备用）
