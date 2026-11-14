# 架构与决策

## 目录

```
config/
  xhs_campaign.yaml   # 推广主题、标题模板、合规词、素材 glob
  xhs_api.yaml        # （可选）开放平台 common_controller、OAuth；自动发帖不依赖此文件
marketing/
  logs/               # xhs_publish.jsonl、YYYY-MM-DD.md
  xiaohongshu/
    sign.py           # MD5 签名（开放平台客户端用）
    client.py         # （可选）common_controller、OAuth、publish_note
    theme.py          # 主题与最新视频 info.md 解析
    composer.py       # 五段式正文、素材枚举、合规检查
    diary.py          # JSONL + 日摘要
    publish_cli.py    # 入口
  XHS_MCP_PUBLISH.md  # 主推：经 xiaohongshu-mcp 发布（HTTP/MCP）
  XHS_OPEN_PLATFORM.md  # 开放平台 API（可选 / 遗留说明）
scripts/
  xhs_publish.py      # 从项目根调用的包装脚本
tools/
  xiaohongshu-mcp/    # 第三方 MCP（Docker Compose），实际发帖经其 HTTP `/api/v1/publish` 等
```

## 决策

- **`info.md` 与推文**：`publish_cli.py` 在 `daily-video` 下读取视频目录内 `info.md` 时，先剔除非教学内容行（生成状态、路径、ID、链接等），再从调用参数类 JSON 中抽取 `questions` / `subject` / `theme` / `输出剧情` 等拼进正文或交给 LLM，避免把「视频已保存为 video_01.mp4」类话术写进小红书。
- **默认不调用外网**：CLI 默认不带 `--execute`，仅生成文案与日记；**自动发帖**走 **xiaohongshu-mcp**（浏览器 + Cookie），见 `marketing/XHS_MCP_PUBLISH.md`，不依赖开放平台发帖接口。
- **开放平台客户端可插拔**：`publish_note.method` 未配置时 `publish_note` 返回 `skipped`；仅在有开放平台资质且需直连 API 时使用 `--execute` 与 `XHS_*`。
- **多账号（开放平台）**：通过 `xhs_api.yaml` 的 `accounts` 与环境变量扩展（见文件内注释）。
