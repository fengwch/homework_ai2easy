#!/usr/bin/env bash
# HomeworkCompass 打包：产出一个自包含的部署 tar 包。
#
# 包里包含：源码（src/）、主题底图（assets/bases/）、启动脚本（tools/run-api.sh）、
# 文档（docs/）、pyproject.toml。解压后目标机只需 python3 + pip install，无需 git。
#
# 用法：
#   bash tools/build.sh              # 产物在 dist/
#   bash tools/build.sh --skip-test  # 跳过测试（不推荐）
#
# 产物：
#   dist/homework-compass-<version>-<git短hash>.tar.gz
#   dist/homework-compass-<version>-<git短hash>.tar.gz.sha256
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SKIP_TEST=0
for arg in "$@"; do
    case "$arg" in
        --skip-test) SKIP_TEST=1 ;;
        -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "未知参数：$arg" >&2; exit 2 ;;
    esac
done

VERSION=$(python3 -c "
import re, pathlib
m = re.search(r'^version\s*=\s*\"([^\"]+)\"', pathlib.Path('pyproject.toml').read_text(), re.M)
print(m.group(1) if m else '0.0.0')
")
HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "nogit")
NAME="homework-compass-${VERSION}-${HASH}"
STAGE="dist/${NAME}"

echo "==> 打包 ${NAME}"

# 1) 打包前必须测试全绿
if [ "$SKIP_TEST" -eq 0 ]; then
    echo "==> 运行单元测试"
    python3 -m pytest tests/unit -q
fi

# 2) 底图完整性：缺一张，线上就会悄悄回落成占位图
echo "==> 校验主题底图"
MISSING=0
for f in assets/bases/*_quest-map.png; do
    [ -f "$f" ] || continue
    SIZE=$(python3 -c "
from PIL import Image
print('ok' if Image.open('$f').size == (2480, 3508) else 'bad')
" 2>/dev/null || echo bad)
    if [ "$SIZE" != "ok" ]; then
        echo "  ✗ $f 尺寸不是 2480x3508" >&2
        MISSING=1
    fi
done
COUNT=$(ls assets/bases/*_quest-map.png 2>/dev/null | wc -l | tr -d ' ')
echo "  底图 ${COUNT} 张"
[ "$COUNT" -ge 10 ] || { echo "  ✗ 底图不足 10 张，拒绝打包" >&2; exit 1; }
[ "$MISSING" -eq 0 ] || { echo "  ✗ 底图校验失败" >&2; exit 1; }

# 3) 组装目录
echo "==> 组装 ${STAGE}"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R src "$STAGE/"
cp -R assets "$STAGE/"
cp -R tools "$STAGE/"
cp -R docs "$STAGE/"
# fonts/ 只有放了实际字体文件才带进包（README 本身不用发）
if compgen -G "fonts/*.ttc" >/dev/null || compgen -G "fonts/*.ttf" >/dev/null \
   || compgen -G "fonts/*.otf" >/dev/null; then
    mkdir -p "$STAGE/fonts"
    cp fonts/*.tt? "$STAGE/fonts/" 2>/dev/null || true
    cp fonts/*.otf "$STAGE/fonts/" 2>/dev/null || true
    echo "  已包含随包字体：$(ls "$STAGE/fonts" | tr '\n' ' ')"
else
    echo "  未放字体文件，目标机需自带中文字体（fc-list :lang=zh）"
fi
cp pyproject.toml README.md "$STAGE/"
# 源码缓存与测试不进包
find "$STAGE" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name "*.pyc" -delete 2>/dev/null || true
# egg-info 是 pip install -e 留下的构建缓存，换机器会失效，不能进包
find "$STAGE" -name "*.egg-info" -type d -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$STAGE/assets/homeworks" 2>/dev/null || true

# 4) 打进 tar 包
echo "==> 生成压缩包"
tar -C dist -czf "dist/${NAME}.tar.gz" "$NAME"
rm -rf "$STAGE"
(
    cd dist
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "${NAME}.tar.gz" > "${NAME}.tar.gz.sha256"
    else
        sha256sum "${NAME}.tar.gz" > "${NAME}.tar.gz.sha256"
    fi
)

echo
echo "完成："
ls -lh "dist/${NAME}.tar.gz" "dist/${NAME}.tar.gz.sha256"
echo
echo "目标机部署："
echo "  tar -xzf ${NAME}.tar.gz && cd ${NAME}"
echo "  python3 -m pip install '.[api]'          # CLI 用 '.[]' 改为 '.'"
echo "  bash tools/run-api.sh 8100                  # HW_BASE_DIR 自动指向 assets/bases"
