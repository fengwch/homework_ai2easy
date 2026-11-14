#!/usr/bin/env bash
# 本地 H5 开发启动：与 HBuilderX「运行到浏览器」同一套环境变量和命令行。
# 直接 `vite` 或只设 UNI_INPUT_DIR 会导致 /main 解析不到（UTS 入口不编译）。
# 用法：bash tools/h5-dev.sh [port]，访问 http://localhost:<port>/web/
set -euo pipefail
HX=/Applications/HBuilderX.app/Contents/HBuilderX
PORT="${1:-5174}"
cd "$(dirname "$0")/.."
INPUT="$PWD"

HX_Version=5.34 \
HX_DEPENDENCIES_DIR="$INPUT/unpackage/cache/uts_cache" \
HX_APP_ROOT="$HX" \
HX_PLUGIN_PATHS='{"compile-dart-sass":"'"$HX"'/plugins/compile-dart-sass","uniapp-cli-vite":"'"$HX"'/plugins/uniapp-cli-vite","uniapp-uts-v1":"'"$HX"'/plugins/uniapp-uts-v1","hbuilderx-language-services":"'"$HX"'/plugins/hbuilderx-language-services","uni_helpers":"'"$HX"'/plugins/uni_helpers","about":"'"$HX"'/plugins/about"}' \
RUN_BY_HBUILDERX=true UNI_HBUILDERX_LANGID=zh_CN \
HX_RUN_DEVICE_TYPE=h5 UNI_PLATFORM=h5 UNI_UTS_PLATFORM=web \
UNI_APPID=__UNI__66F9EC0 UNI_APP_X_DOM2= \
UNI_INPUT_DIR="$INPUT" \
UNI_OUTPUT_DIR="$INPUT/unpackage/dist/dev/web" \
UNI_APP_X_CACHE_DIR="$INPUT/unpackage/cache/.web" \
"$HX/plugins/node/node" --max-old-space-size=5120 --no-warnings \
  -r "$HX/plugins/uniapp-extension/static/kill.js" \
  "$HX/plugins/uniapp-cli-vite/node_modules/@dcloudio/vite-plugin-uni/bin/uni.js" \
  -p h5 --port "$PORT" --host
