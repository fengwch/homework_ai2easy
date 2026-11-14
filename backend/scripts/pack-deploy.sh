#!/bin/bash
# 打包部署压缩包，用于物理机部署
set -e

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
OUT_DIR="${ROOT}/dist"
PKG_NAME="homework-ai2easy-backend"
VERSION="${VERSION:-$(date +%Y%m%d)}"
ZIP_NAME="${PKG_NAME}-${VERSION}.zip"

echo "==> 清理旧构建..."
rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}/${PKG_NAME}"

echo "==> 确保 wire 已生成..."
if [ ! -f "cmd/server/wire_gen.go" ]; then
  echo "运行 make wire..."
  make wire
fi

echo "==> 编译 Linux amd64 二进制..."
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=amd64
go build -ldflags "-s -w -X main.Version=${VERSION}" -o "${OUT_DIR}/${PKG_NAME}/bin/server" ./cmd/server

echo "==> 复制配置与文档..."
mkdir -p "${OUT_DIR}/${PKG_NAME}/configs"
cp configs/config.example.yaml "${OUT_DIR}/${PKG_NAME}/configs/"

# 复制 openapi（处理 docs 可能是符号链接的情况）
mkdir -p "${OUT_DIR}/${PKG_NAME}/docs/api"
if [ -f "docs/api/openapi.yaml" ]; then
  cp docs/api/openapi.yaml "${OUT_DIR}/${PKG_NAME}/docs/api/"
else
  echo "警告: docs/api/openapi.yaml 不存在，Swagger 可能不可用"
  touch "${OUT_DIR}/${PKG_NAME}/docs/api/openapi.yaml"
fi

# 复制 DDL（如有）
if [ -f "scripts/smartstudy_2026-02-16.sql" ]; then
  mkdir -p "${OUT_DIR}/${PKG_NAME}/scripts"
  cp scripts/smartstudy_2026-02-16.sql "${OUT_DIR}/${PKG_NAME}/scripts/"
fi

echo "==> 复制部署文件..."
cp deploy/DEPLOY.md "${OUT_DIR}/${PKG_NAME}/"
cp deploy/start.sh "${OUT_DIR}/${PKG_NAME}/"

echo "==> 创建必要目录..."
mkdir -p "${OUT_DIR}/${PKG_NAME}/logs"
mkdir -p "${OUT_DIR}/${PKG_NAME}/uploads"
touch "${OUT_DIR}/${PKG_NAME}/logs/.gitkeep"
touch "${OUT_DIR}/${PKG_NAME}/uploads/.gitkeep"

echo "==> 设置执行权限..."
chmod +x "${OUT_DIR}/${PKG_NAME}/start.sh"
chmod 755 "${OUT_DIR}/${PKG_NAME}/bin/server"

echo "==> 打包 ZIP..."
cd "${OUT_DIR}"
zip -r "${ZIP_NAME}" "${PKG_NAME}"
cd "${ROOT}"

echo "==> 完成"
echo "部署包: ${OUT_DIR}/${ZIP_NAME}"
ls -lh "${OUT_DIR}/${ZIP_NAME}"
