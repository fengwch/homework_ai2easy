# 漫画分格插件 - Coze 配置说明

插件入口为 `tools/comic_panel_extractor.handler`，执行成功时 Coze 会显示「Execute success」。若**测试仍显示失败**，多半是**返回结果与 Coze 里配置的 Output 不一致**，按下面配置即可。

---

## 1. Input（入参）

在插件「参数 / 入参」里添加，**名称与类型必须一致**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| image | string | 是 | 整页漫画的 base64（可含 data:image/...;base64, 前缀） |
| max_panels | number 或 string | 否 | 期望最大分镜数量，不填则不限制 |

若 Coze 要求入参全是 string，则 `max_panels` 填 `"12"` 这类字符串即可。

---

## 2. Output（出参）— 必须与返回结构一致

插件**成功和失败**时都返回**同一批字段**，仅在取值不同。在 Coze 的「出参 / 返回结构」里按下面声明，**字段名与类型一致**，测试才会通过：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否成功 |
| panel_count | number | 分镜数量（成功时为 ≥0 的整数，失败时为 0） |
| panels | array | 每格信息列表，元素为 object |
| panels[].path | string | 该格临时文件路径（仅服务端有意义） |
| panels[].width | number | 宽度（像素） |
| panels[].height | number | 高度（像素） |
| panel_images | array | 与 panels 顺序一致的 base64 字符串列表；失败时为空数组 [] |
| message | string | 固定为 "ok" 或 "failed" |
| error | string | 成功时为空字符串 ""，失败时为错误信息 |

要点：

- **成功和失败都包含这 6 个字段**：`success`、`panel_count`、`panels`、`panel_images`、`message`、`error`。
- 不要少声明 `error`，也不要让成功时不返回 `error`（代码里已改为成功时返回 `error: ""`）。
- 类型用 Coze 支持的：boolean、number、string、array、object；不要用「文件」等特殊类型表示 base64，用 **string** 即可。

---

## 3. 测试时

- **入参**：至少传入 `image`（一张漫画页的 base64）。可选传 `max_panels`（如 12）。
- **预期**：Execute success 且测试通过。若仍失败，检查 Coze 里 Output 是否与上表**完全一致**（尤其是 `error` 字段和 `panels` 为 array of object）。

---

## 4. 依赖（Coze 环境）

- `numpy`
- `opencv-python-headless`

若 Coze 沙箱报 `numpy.core.multiarray failed to import`，多为环境不支持 OpenCV，可改为通过 HTTP 调用本地/服务器上的分格接口，Coze 内只保留 HTTP 插件。
