#!/usr/bin/env bash
# hw-dispatch.sh — 把 headless 任务派发到 homework_ai2easy 的指定子仓库
#
# 已验证的事实（2026-11-11 实测）：
#   1. 源码安装的 dsh 必须从源码仓目录启动（pnpm dsh），否则依赖解析错位
#   2. headless 会话的工作区 = 进程 cwd = 源码仓目录，不会随任务变化
#   3. 因此本脚本把目标仓库绝对路径写进任务文本，由 agent 显式 cd 过去干活
#
# 用法：
#   ./scripts/hw-dispatch.sh <backend|agent|app|compass> "<任务描述>" [--json]
#   ./scripts/hw-dispatch.sh backend "在 feature 分支实现 xxx，跑通 make test" --json
#
# 退出码：0=任务完成，1=失败（dsh headless 语义，可直接用于 CI 判断）
#
# Author: fengwc2, Email: fengwc2@chinatelecom.cn
set -euo pipefail

DSH_SRC="$HOME/Documents/study/ai_agent/deepseek-harness"
HW_ROOT="$HOME/Documents/homework_ai2easy"

usage() {
  echo "用法: $0 <backend|agent|app|compass> \"<任务描述>\" [--json]" >&2
  exit 1
}

[ $# -ge 2 ] || usage
REPO_ID="$1"; TASK="$2"; shift 2
JSON_FLAG=""
[ "${1:-}" = "--json" ] && JSON_FLAG="--json"

case "$REPO_ID" in
  backend) REPO_PATH="$HW_ROOT/backend";  PROFILE="hw-backend" ;;
  agent)   REPO_PATH="$HW_ROOT/agent";    PROFILE="hw-agent" ;;
  app)     REPO_PATH="$HW_ROOT/app";      PROFILE="hw-app" ;;
  compass) REPO_PATH="$HW_ROOT/HomeworkCompass"; PROFILE="hw-compass" ;;
  *) usage ;;
esac

# 任务文本包装：工作区锚定 + 回收要求（agent 必须显式 cd，硬约束靠任务文本传递）
FULL_TASK="工作区约束：所有文件读写与命令必须先 cd 到 ${REPO_PATH} 内执行，禁止在该目录之外创建或修改文件。
任务：${TASK}
完成后必须输出：1) 改动文件清单（git diff --stat） 2) 测试/lint 执行结果 3) 遗留风险。"

cd "$DSH_SRC"
exec pnpm dsh --profile "$PROFILE" $JSON_FLAG "$FULL_TASK"
