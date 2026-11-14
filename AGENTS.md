<comet-ambient-resume>
<!-- Managed by Comet. Edits inside this block may be replaced by comet init/update. -->
<!-- Contract: comet.resume_probe.v2 -->

## Comet Ambient Resume

在这个仓库中，开始处理需要改动或调查的任务前，如果可能存在活跃 Comet workflow，把当前用户请求传入只读探针：`comet resume-probe . --stdin --json`。

- 如果用户通过宿主明确调用任意 Comet Skill（例如 `@comet`、`/comet`、`@comet-native` 或 `/comet-hotfix`），显式调用优先于本恢复协议；不要运行 resume probe，直接进入被调用的 Skill。
- 如果用户通过宿主明确调用的是非 Comet 的 Skill 或斜杠命令，任务意图已由该调用明确：不要运行 resume probe，直接执行该 Skill。
- 如果你正在 Comet 流程内（包括正在等待用户回复你在流程中提出的问题），不要运行 resume probe；把这类回复（例如方案/选项选择）当作当前 change 的继续，直接按用户的选择推进。
- 只信任返回的 `workflow`、`skill` 和 `entrySource`；它们只由项目配置或无配置兼容回退决定。不得扫描或切换另一套 workflow。
- 如果 probe 返回 `auto_resume`，简短说明选中的 active change，并进入 `nextCommand` 指向的永久入口。不要把状态命令当作恢复入口直接推进。
- 如果 probe 返回 `ask_user`，只问一个简短问题并等待用户回复。
- 如果当前请求未明确调用 Comet Skill，且 probe 返回 `out_of_scope` 或 `none`，不要进入 Comet workflow。
- `out_of_scope` 或 `none` 只表示不要因为这个新请求进入 Comet workflow；它绝不表示要暂停或退出一个已在进行的 Comet 流程。
- 如果配置或状态无效且没有 `nextCommand`，停止并报告原因；不要猜测另一个 workflow。
- 不能只因为存在 active change 就把无关任务挂到该 change。Native 的未提交改动由 Native 入口检查，不由探针自动归因。
</comet-ambient-resume>

<!-- ===== 以下为本工作区的 dsh super agent 总纲（独立于上方 Comet 块，勿混排） ===== -->

## dsh Super Agent 总纲

本目录是**多仓库工作区**（根目录无 git）：backend(Go Kratos 主服务) / agent(Python FastAPI AI 层) /
app(uni-app x 前端) / HomeworkCompass(独立工具)。调度信息以 `projects.yaml` 为唯一事实来源。

1. 任何仓库操作前先读 `projects.yaml` 确认 id、path、commands、rules。
2. 调用链契约：`app → backend(HTTP) → agent(HTTP:8011)`。**app 禁止直连 agent**；
   改接口字段必须三端协调（先用 contract-check skill 核对，禁止单端擅改）。
3. 各仓独立 git：写任务先建 feature/ 分支，backend/agent/app 主分支 master、compass 主分支 main。
4. 只跑注册表声明过的 commands；注册表之外的命令逐条向用户确认。
5. 派发跨仓写任务时遵守依赖顺序：先 backend 后 app；compass 与其他仓可并行。
6. 密钥（DASHSCOPE_API_KEY、MySQL/Redis 等）只走环境变量，输出中只报字段名不报值。
7. compass 的"pending 非空拒绝出图"是硬校验，任何任务不许绕过。
8. 每次派发后必须回收：git diff --stat、test/lint 结果、遗留风险。

