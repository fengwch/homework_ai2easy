#!/usr/bin/env bash
set -euo pipefail

# 在物理机上安装运行环境（Python 虚拟环境 + 依赖）
# 假设本脚本位于解压后的项目目录 scripts/ 下

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> 使用 Python 解释器: ${PYTHON_BIN}"

if [ ! -d ".venv" ]; then
  echo "==> 创建虚拟环境 .venv"
  "${PYTHON_BIN}" -m venv .venv
fi

echo "==> 激活虚拟环境并安装依赖"
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> 创建运行所需目录 logs/ 与 uploads/"
mkdir -p logs uploads

cat <<'EOF'
==> 安装完成

下一步：
1. 在项目根目录配置 .env（可从 .env.example 复制修改）：
   cp .env.example .env
   # 按需要填入 DASHSCOPE_API_KEY / TTAPI_API_KEY / GEMINI_API_KEY 等

2. 启动服务（开发或生产二选一）：

   # 开发环境（单进程）
   source .venv/bin/activate
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8001

   # 生产环境（多进程 Gunicorn）
   source .venv/bin/activate
   gunicorn -c gunicorn.conf.py api.main:app

3. 浏览器访问或用 curl 自检：
   curl http://127.0.0.1:8001/health

EOF

