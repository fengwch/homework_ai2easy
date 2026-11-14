#!/usr/bin/env bash
# 目标生成器 FastAPI 启动脚本。
# 绑定 0.0.0.0（不是 127.0.0.1）：浏览器和 Node 用 localhost 时会先解析到 ::1，只绑 IPv4 回环会连不上。
# 用法：bash tools/run-api.sh [port]（默认 8100）
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${1:-8100}"
# .env 里的 DASHSCOPE_API_KEY 只在本进程生效，不落进代码或配置
set -a; [ -f .env ] && . ./.env; set +a
# 主题底图相对本脚本解析：无论从哪个目录启动都能找到 assets/bases
export HW_BASE_DIR="${HW_BASE_DIR:-$PWD/assets/bases}"
# 随包字体优先：fonts/ 下放了 ttc/ttf 就不依赖服务器装中文字体
if [ -z "${HW_FONT:-}" ]; then
    for f in "$PWD"/fonts/*.ttc "$PWD"/fonts/*.ttf "$PWD"/fonts/*.otf; do
        [ -f "$f" ] && { export HW_FONT="$f"; break; }
    done
fi
exec env PYTHONPATH=src python3 -m uvicorn homework_compass.api:app --host 0.0.0.0 --port "$PORT"
