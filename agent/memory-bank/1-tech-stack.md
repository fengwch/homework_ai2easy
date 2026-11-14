# 技术栈与约束（节选）

- **语言**：Python 3；配置 **YAML**；HTTP **requests**。
- **小红书 API**：`common_controller` + MD5 签名（`method?appId=...&timestamp=...&version=...` + appSecret）；OAuth `oauth.getAccessToken` / `oauth.refreshToken`。
- **密钥**：仅 `.env` 与本地 `marketing/xiaohongshu/.token_cache.json`（已 gitignore）。
