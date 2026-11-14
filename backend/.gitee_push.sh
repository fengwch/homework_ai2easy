#!/bin/bash
# Gitee 仓库推送脚本
# 使用方法：./.gitee_push.sh <gitee_repo_url>
# 例如：./.gitee_push.sh https://gitee.com/homework_ai2easy/backend.git

if [ -z "$1" ]; then
    echo "❌ 错误: 请提供 Gitee 仓库地址"
    echo ""
    echo "使用方法:"
    echo "  $0 <gitee_repo_url>"
    echo ""
    echo "示例:"
    echo "  $0 https://gitee.com/homework_ai2easy/backend.git"
    echo ""
    echo "或者使用 SSH 地址:"
    echo "  $0 git@gitee.com:homework_ai2easy/backend.git"
    exit 1
fi

REPO_URL="$1"
REPO_NAME=$(basename "$REPO_URL" .git)

echo "🚀 正在连接到 Gitee 仓库: $REPO_URL"
echo ""

# 检查是否已经存在 origin 远程仓库
if git remote get-url origin >/dev/null 2>&1; then
    CURRENT_URL=$(git remote get-url origin)
    echo "⚠️  已存在远程仓库 origin: $CURRENT_URL"
    read -p "是否要更新为新的地址? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote set-url origin "$REPO_URL"
        echo "✅ 已更新远程仓库地址"
    else
        echo "❌ 取消操作"
        exit 1
    fi
else
    git remote add origin "$REPO_URL"
    echo "✅ 已添加远程仓库 origin"
fi

# 检查当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 当前分支: $CURRENT_BRANCH"
echo ""

# 推送代码
echo "📤 正在推送代码到 Gitee..."
if git push -u origin "$CURRENT_BRANCH"; then
    echo ""
    echo "✅ 代码已成功推送到 Gitee!"
    echo ""
    echo "📋 仓库信息:"
    echo "  - 远程地址: $REPO_URL"
    echo "  - 分支: $CURRENT_BRANCH"
    echo ""
    echo "🔗 访问仓库: $(echo "$REPO_URL" | sed 's/\.git$//')"
else
    echo ""
    echo "❌ 推送失败，请检查:"
    echo "  1. Gitee 仓库是否已创建"
    echo "  2. 是否有推送权限"
    echo "  3. 网络连接是否正常"
    echo ""
    echo "💡 提示: 如果仓库不存在，请先在 Gitee 创建仓库:"
    echo "  https://gitee.com/projects/new"
    exit 1
fi

