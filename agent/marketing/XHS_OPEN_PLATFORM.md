# 小红书开放平台 API（可选 / 遗留）

> **当前主推的发帖能力**：请使用 **xiaohongshu-mcp**，见 [XHS_MCP_PUBLISH.md](./XHS_MCP_PUBLISH.md)。**无需**开放平台「笔记发布」类接口权限即可在本机完成图文发布。

以下内容仅在你**仍需**对接官方 `ark.xiaohongshu.com` / `common_controller`（例如企业自建应用）时参考；个人开发者多数场景可忽略。

---

若你以**个人**身份开发，开放平台对**店铺类开发者**等有主体与类目限制（例如 [开放平台文档相关说明](https://open.xiaohongshu.com/document/developer/file/32)），可能**无法**开通用于自动发帖的开放接口。

本仓库软文流水线 **`python scripts/xhs_publish.py`** 默认只生成文案与日记；自动发帖请走 **MCP**（见上文），勿与开放平台混用。

`marketing/xiaohongshu/client.py` 与 `config/xhs_api.yaml` 保留为可选封装；需 **AppId / Secret、OAuth** 时再放入 `.env`（勿提交）。

---

## 附录：开放平台注册与 method（仅备用）

接口与菜单名称以 [小红书开放平台](https://open.xiaohongshu.com) 当前页面为准。

### 1. 注册与主体

- 使用企业、个体工商户或个人开发者账号注册开放平台（以平台规则为准）。

### 2. 创建应用与权限

- 在控制台创建应用，申请与目标一致的 API；配置 **授权回调地址**（OAuth）。

### 3. 凭证

- 审核通过后记录 **App ID**、**App Secret**；通过 OAuth 换取 **accessToken** / **refreshToken**（见 `marketing/xiaohongshu/client.py`）。

### 4. 业务 method

- 将网关、`publish` / `upload` 等 **method** 与请求体填入 `config/xhs_api.yaml`。未配置时客户端不会发起虚构业务请求。

### 5. 多账号

- 通常 **一个授权对应一个小红书账号**；可在 `xhs_api.yaml` 的 `accounts` 中扩展。

### 6. 参考

- 授权与签名：Apifox「小红书 API」《授权流程》《签名算法》；签名规则为 `method?appId=...&timestamp=...&version=...` 末尾拼接 `appSecret` 后 MD5。
