# 通过 xiaohongshu-mcp 发布（推荐）

本项目的**自动发帖**不依赖 [小红书开放平台](https://open.xiaohongshu.com) 的 **API 权限**，而是使用本地部署的 **[xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp)**（浏览器自动化 + 已登录 Cookie），经 **HTTP API** 或 **MCP 工具**发布图文/视频。

## 1. 前置

- 按 [tools/xiaohongshu-mcp/README.md](../tools/xiaohongshu-mcp/README.md) 启动 Docker，完成**扫码登录**，`data/cookies.json` 有效。
- 服务默认：`http://127.0.0.1:18060`（健康检查：`GET /health`）。

## 2. 与「软文流水线」的配合

1. 直接运行（默认会生成文案并调用本地 MCP HTTP 发布）：

   ```bash
   python3 scripts/xhs_publish.py
   ```

2. 如只想生成不发布，可关闭自动发布：

   ```bash
   python3 scripts/xhs_publish.py --no-mcp-publish
   ```

3. 素材路径已对齐：容器读取 `/app/images/...`，宿主机对应 `agent/imgs/...`（由 compose 直接挂载）。

## 3. HTTP 发布图文（示例）

`POST /api/v1/publish`，JSON 字段与上游一致（节选）：

| 字段 | 说明 |
|------|------|
| `title` | 标题（小红书限制约 20 字，见上游 README） |
| `content` | 正文 |
| `images` | 图片路径数组，**至少 1 张**；Docker 内须为可读绝对路径（如 `/app/images/1.jpg`） |
| `tags` | 话题标签，可选 |

示例（在宿主机用 `curl`，路径按你实际挂载调整）：

```bash
curl -sS -X POST http://127.0.0.1:18060/api/v1/publish \
  -H "Content-Type: application/json" \
  -d '{
    "title": "辅导作业太累？试试把题目变成故事",
    "content": "正文……",
    "images": ["/app/images/cover.jpg"],
    "tags": ["亲子教育", "辅导作业"]
  }'
```

视频发布：`POST /api/v1/publish_video`，字段 `video` 为容器内可访问的本地视频路径。

## 4. MCP（Cursor / Claude 等）

配置见项目根目录 `.cursor/mcp.json`（`http://127.0.0.1:18060/mcp`）。在对话中调用上游提供的 **发布图文** 等工具即可（需会话未过期，参见 tools README 中的 session 说明）。

## 5. 与开放平台代码的关系

仓库内 `marketing/xiaohongshu/client.py`、`config/xhs_api.yaml` 为**历史/可选**的开放平台 `common_controller` 封装；**日常发帖请以 xiaohongshu-mcp 为准**，无需申请开放平台发帖接口。

开放平台说明（备用）见 [XHS_OPEN_PLATFORM.md](./XHS_OPEN_PLATFORM.md)。
