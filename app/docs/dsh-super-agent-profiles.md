# dsh super agent profile 配置（homework_ai2easy 专用）— 实测版

> 2026-11-11 已在本机实测验证。源码仓：`~/Documents/study/ai_agent/deepseek-harness`，
> DSH_HOME=`~/.dsh`（实测确认）。

## 一、profile 已创建（5 个，位于 ~/.dsh/profiles/）

| profile | bundles | 形态 | 用途 |
|---|---|---|---|
| hw-root | base + web-app | 交互式 Web UI | 全仓任务、契约变更、巡检汇总 |
| hw-backend | base + headless | 一次性任务 | backend 子仓派发 |
| hw-agent | base + headless | 一次性任务 | agent 子仓派发 |
| hw-app | base + headless | 一次性任务 | app 子仓派发 |
| hw-compass | base + headless | 一次性任务 | compass 子仓派发 |

创建方式为手工建目录（package.json 声明 bundles + 空 cordis.yml/patch），
已通过 `--dump-config` 验证配置树合成正常，并通过探针任务验证端到端可用（退出码 0）。

## 二、调用命令（源码模式硬约束）

**源码安装的 dsh 必须从源码仓目录启动**——从其他目录直接调 bin.ts 会因
`@deepseek-ai/cordis` 依赖解析错位报错（实测确认）。因此：

```bash
# 交互式全仓会话
cd ~/Documents/study/ai_agent/deepseek-harness
pnpm dsh --profile hw-root

# 派发子仓任务（推荐用包装脚本，见下）
~/Documents/homework_ai2easy/scripts/hw-dispatch.sh backend "实现 xxx 并跑通 make test"
```

**关键行为（实测）**：headless 会话的工作区 = 进程 cwd = 源码仓目录，
不会随任务变化。目标仓库路径由 `hw-dispatch.sh` 写入任务文本，
agent 显式 `cd` 过去执行——这是软约束，硬约束加固见"下一步"。

## 三、headless app 可用参数（实测 --help 确认）

```bash
pnpm dsh --profile hw-backend "任务文本"          # 位置参数即任务；"-" 从 stdin 读
pnpm dsh --profile hw-backend --json "任务"       # NDJSON 事件流输出（脚本解析友好）
pnpm dsh --profile hw-backend --session-id <id> "继续"   # 续接已持久化会话
```

退出码：任务完成=0，失败=1（可直接用于 CI / 脚本判断）。

## 四、模型与权限现状（读自 ~/.dsh/settings.yaml）

- 默认模型：`deepseek-official / deepseek-v4-flash`（reasoningEffort: high）
- 自定义网关：`aigw-fwc`（含 deepseek-v4-pro / glm-5.x / kimi / qwen 系列），
  密钥走 `AIGW_FWC_API_KEY` 等环境变量
- ⚠️ 全局 `permission.defaultPreset: danger-full-access` —— 对派发任务偏宽，
  见"风险与下一步"

## 五、验证清单（已完成 / 待办）

- [x] hw-root / hw-backend `--dump-config` 配置树合成正常
- [x] hw-backend 探针任务端到端跑通（退出码 0，cwd 确认）
- [x] headless `--help` 参数确认（--json / --session-id）
- [ ] hw-root Web UI 会话中选择 homework 工作区并触发 project-status 巡检
- [ ] PreToolUse 写入守卫 hook（见下）

## 六、风险与下一步（按优先级）

1. **[高] 工作区约束是软约束**：当前靠任务文本要求 agent cd 到目标仓，agent 违规时无拦截。
   加固方案：给 hw-* profile 的 cordis.patch.yml 加 insert 条目，挂
   `@deepseek-ai/dsh-hooks-claude-code` 插件 + 自定义 hooks.json，
   在 PreToolUse(write|edit) 校验目标路径必须位于 homework_ai2easy 下。
   insert 格式已从本机 web/headless profile 实测文件确认，hooks 脚本逻辑 [待核实: 读
   node_modules/@deepseek-ai/dsh-hooks-claude-code 的输入输出约定后编写]。
2. **[高] 全局 danger-full-access 偏宽**：建议将 hw-* 会话改为 workspace-write
   （需在 dump-config 里确认 permission 配置键后再改 settings.yaml 或 patch）。
3. **[中] headless 插件隔离**：hw-* profile 的 node_modules 为空，需要 MCP 等插件时
   `pnpm dsh plugin --profile hw-backend add <pkg>` 逐个装。
4. **[低] comet hook 全局生效**：hooks.json 的 PreToolUse 对 write|edit 已挂
   comet 路由器，hw-* profile 未挂载，行为差异注意观察。
