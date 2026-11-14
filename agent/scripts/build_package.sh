#!/usr/bin/env bash
set -euo pipefail

# 打包当前项目为可部署压缩包（不包含虚拟环境、git、日志、上传文件等）

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PKG_NAME="ai-agent-$(date +%Y%m%d%H%M%S).zip"

echo "==> 打包项目到 ${PKG_NAME} (zip)"

# 使用 zip 递归打包，排除虚拟环境、git、日志、上传目录以及大体积/非必要资源
zip -r "${PKG_NAME}" . \
  -x ".git/*" \
  -x ".venv/*" \
  -x "venv/*" \
  -x "__pycache__/*" \
  -x "*.pyc" \
  -x "logs/*" \
  -x "uploads/*" \
  -x "docs/*" \
  -x "imgs/*" \
  -x "tests/*"

echo "==> 打包完成：${PKG_NAME}"
echo "将该文件上传到物理机后，在目标目录执行（示例）："
echo "  unzip ${PKG_NAME}"

