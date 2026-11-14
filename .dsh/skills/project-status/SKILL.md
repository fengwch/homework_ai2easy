---
name: project-status
description: 巡检 homework_ai2easy 工作区全部 4 个子仓库：分支、未提交改动、最近提交、编译/测试健康度，输出结构化报告。当用户说"巡检"、"看下项目状态"时使用。
---

# homework_ai2easy 全仓巡检

## 步骤

1. 读取 `projects.yaml`，按 repos 顺序逐仓执行 `commands.check`（在该子仓目录内）。
2. 每仓收集：当前分支、未提交/未跟踪文件数、最近 3 条提交。
3. 深度巡检（用户要求时）再跑 `commands.test`；backend 先 `make build-fast` 验证编译。
4. 汇总报告：

   | 仓库 | 分支 | 未提交 | 最近动作 | 风险 |
   |---|---|---|---|---|

   末尾附"建议动作"清单。

## 工作区特有检查项

- agent 与 backend 端口约定：确认 agent 的 8011 与 backend 配置一致（只读 configs/config.dev.yaml 的引用关系，不打印密钥）。
- app 是否存在直连 agent 的残留代码（grep `8011` / agent 地址于 app/frontend）——存在即列为契约违规。
- compass 若有未提交改动且涉及 api.py / tools/run-api.sh，提示"服务形态变更，上线文档需同步"。

## 边界

- 全程只读：禁止 commit / checkout / stash / push。
- 任何仓库 check 失败：记录报错原文继续下一仓，不中断巡检。
- 配置文件里出现密钥字段时只报字段名，不输出值。
