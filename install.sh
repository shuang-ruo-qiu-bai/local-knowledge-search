#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/shuiqiu94-creator/book-chat.git"

# Detect target directory
if [ -d "$HOME/.claude/skills" ]; then
    TARGET="$HOME/.claude/skills/wenge-research"
elif [ -d "$HOME/.agents/skills" ]; then
    TARGET="$HOME/.agents/skills/wenge-research"
else
    TARGET="$HOME/wenge-research"
fi

echo "==> 安装到: $TARGET"

# Clone or update
if [ -d "$TARGET" ]; then
    echo "==> 目录已存在，更新中..."
    cd "$TARGET" && git pull
else
    git clone "$REPO_URL" "$TARGET"
fi

# Install Python dependencies
echo "==> 安装 Python 依赖..."
pip3 install chromadb sentence-transformers rank-bm25 -q

echo ""
echo "==> 安装完成！"
echo ""
echo "下一步："
echo "  1. 准备知识库目录（默认 ~/wenge-knowledge-base），按以下结构放书："
echo "     knowledge-base/"
echo "     ├── books/文革/"
echo "     ├── raw/文革/"
echo "     ├── notes/"
echo "     └── topics/"
echo ""
echo "  2. 建立索引："
echo "     cd \"$TARGET\" && python3 scripts/rag_index.py"
echo ""
echo "  3. 开始搜索："
echo "     python3 \"$TARGET/scripts/rag_search.py\" --root ~/wenge-knowledge-base \"你的问题\""
