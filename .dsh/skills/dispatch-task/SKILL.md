---
name: dispatch-task
description: 把 bounded task 派发到 homework_ai2easy 的某个子仓库，在独立 headless 会话执行并回收结果。当用户说"派发任务到 backend/agent/app/compass"时使用。
---

# 任务派发（多仓库工作区版）

## 步骤

1. 从 `projects.yaml` 确认目标仓库 id（backend / agent / app / compass），读取其 path、commands、rules、branch。
2. 与用户确认三要素：目标仓库 id、bounded 任务描述（明确完成判据）、权限边界（只读/可写）。
3. 派发执行（实测约束见 docs/dsh-super-agent-profiles.md：源码模式必须从源码仓启动，
   headless 工作区=源码仓 cwd，目标仓库路径须写进任务文本）：

   ```bash
   # 推荐方式：包装脚本（已把目标仓库绝对路径锚定进任务文本）
   ~/Documents/homework_ai2easy/scripts/hw-dispatch.sh <backend|agent|app|compass> "<任务描述>" [--json]

   # 等价手敲
   cd ~/Documents/study/ai_agent/deepseek-harness
   pnpm dsh --profile hw-<id> "工作区：cd 到 /Users/fengwanchang/Documents/homework_ai2easy/<path>。任务：..."
   ```

   - `--json`：NDJSON 事件流输出，脚本化回收用
   - `--session-id <id>`：续接已持久化会话（多轮派发）
4. 回收结果：改动文件（`git diff --stat`）、test/lint 结果、遗留风险。

## 本工作区特有规则

- **调用链纪律**：涉及 app+agent 两端的改动，必须拆成"backend 改造 → app 对接"两步，
  派发给 backend 和 app 的写任务不能并行（先做依赖方 backend）。
- **契约变更**：若任务会改 backend↔agent 的接口字段，先走 contract-check skill
  确认三端（app/backend/agent）的字段命名协调方案，再派发。
- **compass 独立**：与其他三仓无代码依赖，可安全并行。
- 各仓分支纪律按各自仓库执行（backend/agent/app 在 master，compass 在 main），
  写任务一律先建 feature/ 分支，不许直接改主分支。
- headless 用独立 profile：web profile 的插件不可用，需要的先
  `dsh plugin --profile hw-<id> add <插件>`。

## 边界

- 一个子仓库同时只允许一个写任务。
- 任务失败重试最多 2 次，之后停手汇报，不猜。
