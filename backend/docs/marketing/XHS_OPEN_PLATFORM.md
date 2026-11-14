# 小红书开放平台准备指引

## 个人开发者 / 仅输出软文（当前推荐路径）

若你以**个人**身份开发，开放平台对**店铺类开发者**等有主体与类目限制（例如 [开放平台文档相关说明](https://open.xiaohongshu.com/document/developer/file/32) 中涉及「个人店铺」与开发者开通条件——**以页面最新规则为准**），可能**无法**开通用于自动发帖的接口。

本仓库的**主推用法**是：

- 运行 `python scripts/xhs_publish.py`（**不要**加 `--execute`）：只生成标题、正文、话题与素材清单，并写入 `marketing/logs/`，**不调用任何小红书 HTTP 接口**。
- 将终端或日志里的正文复制到小红书 App **手动发布**；配图/视频使用脚本打印的本地路径自行上传。

`marketing/xiaohongshu/client.py` 与 `config/xhs_api.yaml` 中的 API 封装**保留作可选**：仅当你日后具备企业/符合条件应用并获批接口时再使用。

---

在启用「自动发布」前，请完成以下步骤。接口与菜单名称以 [小红书开放平台](https://open.xiaohongshu.com) 当前页面为准。

## 1. 注册与主体

- 使用企业、个体工商户或个人开发者账号注册开放平台（以平台规则为准）。
- 电商/店铺类能力与「社区笔记」类能力可能分属不同产品线；若你的目标是 **UGC 笔记发布**，请在控制台确认你的应用类目是否包含 **内容发布 / 笔记** 等相关权限包。

## 2. 创建应用

- 在控制台创建应用，应用描述建议写清场景（例如：家长教育类辅助工具、内容发布工具）。
- 配置 **授权回调地址**（OAuth `redirect_uri`），需与后续换取 `code` 时使用的地址一致。

## 3. 申请接口权限

- 在应用内申请 **笔记发布、素材上传** 等与目标一致的 API（名称以控制台为准）。
- 审核通过前，或未申请接口时：运行 `python scripts/xhs_publish.py`（不加 `--execute`）即可仅生成文案与日记，不调用线上接口。

## 4. 凭证与环境变量

审核通过后记录 **App ID（appId）**、**App Secret（appSecret）**。

通过浏览器完成 OAuth 授权后，用返回的 `code` 换取 **accessToken** 与 **refreshToken**（本仓库提供 `oauth.getAccessToken` 调用示例，见 `marketing/xiaohongshu/client.py`）。

将敏感信息写入项目根目录 **`.env`**（勿提交），参考根目录 `.env.example` 中的 `XHS_*` 变量说明。

## 5. 业务接口 method 名

开放平台对「笔记发布」的 **method**、请求体字段可能随类目调整。请在控制台下载或查阅 **与你应用类目匹配的 API 文档**，将：

- 网关地址（默认与 OAuth 相同：`https://ark.xiaohongshu.com/ark/open_api/v3/common_controller`）
- `publish` / `upload` 等方法的 **method 字符串**
- 请求体 JSON 结构

填写到 `config/xhs_api.yaml` 的 `publish_note`、`upload_image` 等节。未配置时，客户端仍会完成 **鉴权与签名**，但发布步骤需在拿到正式文档后补全参数。

## 6. 多账号

通常 **一个授权对应一个小红书账号**。多账号需要多次 OAuth 或按平台规则绑定多店铺/多主体；可在 `config/xhs_api.yaml` 的 `accounts` 数组中为每个账号配置独立的 token 缓存路径或环境变量后缀（见该文件注释）。

## 7. 参考文档（第三方整理，以官方为准）

- 授权与签名算法摘要：Apifox「小红书 API」中的《授权流程》《签名算法》。
- 签名规则：`method?appId=...&timestamp=...&version=...` 末尾拼接 `appSecret` 后做 MD5。
