# Outcome

家长打开首页（`pages/child/list.uvue`）后：①在上方功能区一屏内「上传作业」或「查看作业列表」；②在下方看到当前家庭的孩子卡片，点卡片切换当前孩子，点「编辑」进入档案编辑。孩子卡片不再承载上传或作业入口。

从「上传作业」或作业列表内的扫描入口发起作业后，按设计文档核心流程（①作业接入 → ②解析与确认 → ③生成目标图 → ④选择再编辑 → ⑤下载）把老师发的作业变成一张可打印的 A4 目标图。解析沿用 HomeworkCompass 引擎的「零杜撰、零遗漏、歧义必拦」：有未确认项时不出图。

需求来源：`HomeworkCompass/每日作业目标生成器-方案设计文档.md`（用户指定，覆盖主流程 ①–⑤；⑥打印由用户在自己设备上完成，不实现），以及用户 2026-11-08 明确追加的两个需求（首页功能区重排、孩子卡片优化）。设计文档中超出引擎能力的部分（多种版式骨架、AI 风格底图、LLM 解析、对话式形态）不在本次实现内，见非目标。

# Scope

- 旧实现全部删除：作业列表页「目标图」按钮、`pages/learning/homework-compass.uvue`、`api/homeworkCompass.ts`、`utils/compassEnv.ts`、`pages.json` 对应路由。
- 首页功能区：`pages/child/list.uvue` 上半部新增「作业工作台」功能区，并列「上传作业」与「查看作业列表」两个大卡，下方为「作业目标生成器」次级入口。上传与作业列表从孩子卡片移出。
- 首页孩子卡片重做：只负责「展示 + 选中 + 编辑 + 进入目标生成器」，不再有上传按钮。当前选中态清晰可辨；触控区 ≥ 44px；状态徽章用文字 + 颜色双编码；空态/加载/错误态完整。
- 新前端按五屏流程实现；HTTP 层沿用已有 FastAPI（`HomeworkCompass/src/homework_compass/api.py`），缺口在同文件补接口。
- `.env` 新增 `VITE_COMPASS_API`（独立域名），Compass 前端基址只读该变量，不写死 localhost；`.env` 同步开发/生产两套值。

## 目录结构

### 新建

- `app/frontend/pages/compass/input.uvue` — ①输入屏：粘贴框、图片 OCR；收集原文并调 `/api/parse`。
- `app/frontend/pages/compass/confirm.uvue` — ②确认屏：逐项编辑、歧义项置顶高亮、处理完才放行。
- `app/frontend/pages/compass/candidates.uvue` — ③候选屏：5 种配色并排预览，「换一批」。
- `app/frontend/pages/compass/edit.uvue` — ④编辑屏：改标题口号、按项改文字、换配色。
- `app/frontend/pages/compass/download.uvue` — ⑤下载屏：A4 图展示、保存提示、打印贴士。
- `app/frontend/api/compass.ts` — Compass HTTP 封装（独立基址，不经 `api/http.ts`）。
- `app/frontend/stores/compass.ts` — 跨屏状态：childId、ParsedHomework JSON、选中配色、渲染结果。
- `app/frontend/components/home/ChildCard.uvue` — 首页孩子卡片（新建，替代现有的 `components/business/ChildCard.uvue`，后者字段与行为不匹配且未在首页使用）。

### 修改

- `app/frontend/pages/child/list.uvue` — 上半部改为「作业工作台」功能区（上传作业 / 查看作业列表）；孩子卡片改用新组件；删除卡片上的上传/查看列表按钮及对应死代码（`goToUpload`、`v-if="false"` 的按钮、`list-btn-full` 等旧样式）；更新首次引导文案。
- `app/frontend/pages.json` — 注册 5 个新页面，移除 `pages/learning/homework-compass`。
- `app/frontend/pages/assignment/list.uvue` — 移除「目标图」按钮与 `goToCompass`；空态按钮文案与新增上传入口保持一致。
- `HomeworkCompass/src/homework_compass/api.py` — 按新前端需要补齐接口（如候选批量渲染），保持「pending 非空返回 409」。

### 删除

- `app/frontend/pages/learning/homework-compass.uvue` — 被五屏流程替代。
- `app/frontend/api/homeworkCompass.ts` — 被 `api/compass.ts` 替代。
- `app/frontend/utils/compassEnv.ts` — 合并进 `api/compass.ts`。
- `app/frontend/components/business/ChildCard.uvue` — 与首页卡片职责重复；首页改用新组件后删除（若 grep 确认无其他引用）。

### 明确不建

- 不建独立的前端渲染层或组件库 — 页面直接复用现有 uvue 样式约定。
- 不建 PDF 生成 — 引擎无 PDF 依赖，本次只交付 PNG。
- 不建新的底部 Tab — 现有三 Tab（首页 / 添加小孩 / 我的）保持；上传是首页操作，不进 Tab。

# 非目标

- 不做作业列表页的「目标图」入口。
- 不做 6 种版式骨架 / 8 款皮肤 / AI 风格底图（引擎目前只有 `quest-map` 骨架 + 5 个色板，无底图库）。
- 不接 LLM 解析（`/api/parse` 保持 `NaiveExtractor`）。
- 不做「和昨天一样」历史模板。
- 不做对话式形态。
- 不做孩子卡片的作业数量统计（后端当前没有按孩子聚合的接口，不为此新增接口）。

# Decisions

- D1 入口位置：**首页顶部「作业工作台」功能区**，并列「上传作业」与「查看作业列表」两个大卡（用户确认，2026-11-08 修订；取代原「孩子卡片按钮」方案）。孩子卡片上**不再**有上传或作业列表入口。
- D2 旧实现：删旧前端，保留 FastAPI（用户确认）。
- D3 输入屏：粘贴框为主 + 图片 OCR（`/api/parse/image`）；「用昨天的」暂不做。
- D4 确认屏：逐项可编辑科目/任务/数量/要求/优先级；歧义项置顶高亮，全部处理完才可进入下一步。
- D5 候选/编辑屏：引擎只有一个骨架，因此「候选」= 5 种配色一次生成并排预览；选中后进入编辑屏，可改标题口号、按项改文字、换配色重生成。
- D6 下载屏：显示 A4 PNG + 保存提示 + 打印贴士（A4、实际大小、不缩放）；PDF 不做。
- D7 目标生成器入口：位于首页「作业工作台」功能区、两张主卡下方的「作业目标生成器」次级入口，携带当前选中孩子 `childId`；当前无选中孩子时不可用并提示先选孩子。
- D8 孩子卡片：只承载展示与孩子级操作（选中、编辑）。选中态用边框 + 底色 + 勾选徽章三重编码（不只靠颜色）；年级缺失显示「未设置年级」并可点击直达编辑；卡片整体触控高度 ≥ 88rpx，编辑按钮触控区 ≥ 44px。
- D9 工作台卡片用 SVG/图标字体以外的原生 view 绘制图标块（uni-app x 无 SVG 组件），不使用 emoji 作功能图标；保留 emoji 仅作为品牌/情绪装饰不用于可点击控件。
- D10 扫描流程不动：`scan.uvue` 保持现有「扫描 → 识别 → 学习」路径，其 `onShow` 的 `reLaunch` 兜底也保留（用户确认，2026-11-08）。
- D12 Compass 服务独立部署、独立域名：前端基址仅来自 `.env` 的 `VITE_COMPASS_API`，开发与生产各配一套；不在源码里回落到 localhost（用户确认，2026-11-08）。
- D11 首页布局（用户看效果图后确认，图见 `.ego/home-mock/home-after.html`）：自上而下为问候语 → 「作业工作台」（两张并列大卡 + 下方「作业目标生成器」次级入口）→ 孩子卡片列表 → 现有三 Tab。「作业目标生成器」**不与两卡并列**，而是作为两卡下方的次级入口。孩子卡片选中态为「主色描边 + 浅主色底 + 右上角勾选徽章」。无选中孩子时生成器入口置灰并显示「请先选择孩子」。

# 验收示例

- A1 作业工作台：首页出现「上传作业」与「查看作业列表」两个并列卡；点击「上传作业」进入扫描页，点击「查看作业列表」进入作业列表页；孩子卡片上不再出现上传或查看列表按钮。
- A2 目标生成器：当前有选中孩子时，点击「作业目标生成器」进入输入屏且 `childId` 生效；无选中孩子时提示先选孩子；作业列表页不再出现「目标图」。
- A3 输入：粘贴老师原文 → 解析 → 进入确认屏；未粘贴/纯表情时提示「没有识别到作业内容」。
- A4 确认：清单展示科目/任务/数量/要求/重要标记；歧义项置顶并以红色高亮；全部处理净后「生成」可用。
- A5 歧义：存在 pending 时直接调用生成返回 409，页面显示逐条原因，不出图。
- A6 候选：一次生成 5 个配色的 A4 预览（2480×3508@300dpi）；「换一批」重新生成。
- A7 编辑：能修改标题口号与任一项的文字，修改后重新生成反映到图上。
- A8 下载：显示最终 A4 图，提供具体可执行的保存方式与打印贴士。
- A9 孩子卡片：每张卡片显示头像（无图时取姓名首字）、姓名、年级（缺失显示「未设置年级」）；点击卡片切换当前孩子并更新选中态；点击「编辑」进入该孩子编辑页。
- A10 卡片状态：选中态同时以边框、底色与勾选徽章表达，不只依赖颜色；卡片及编辑按钮触控区 ≥ 44px；加载中显示骨架/加载态，加载失败显示重试按钮，无孩子时显示空态引导。
