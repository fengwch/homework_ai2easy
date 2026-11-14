# 实施计划（动态）

## 小红书推广流水线

- [x] 配置 `config/xhs_campaign.yaml`、`config/xhs_api.yaml`（后者仅开放平台备用）
- [x] 主题推导 `marketing/xiaohongshu/theme.py`（introduce + 最新 `uploads/vedio`）
- [x] 文案 `composer.py`（合规词表、可选 LLM）
- [x] 客户端 `client.py` + `sign.py`（开放平台可选）
- [x] 日记 `diary.py`（jsonl + 按日 md）
- [x] CLI `publish_cli.py` / `scripts/xhs_publish.py`
- [x] 自动发帖路径文档化：`marketing/XHS_MCP_PUBLISH.md`（xiaohongshu-mcp HTTP/MCP）
- [ ] （可选遗留）具备开放平台发帖资质后，在 `xhs_api.yaml` 填写 `publish_note.method` 并使用 `--execute`
