#!/usr/bin/env bash
set -euo pipefail

PROJECT="${1:-$(dirname "$0")/../mathlib_project}"
cd "$PROJECT"
echo "正在同步 Mathlib 依赖..."
lake update
if [ ! -f ".lake/packages/mathlib/.lake/build/lib/lean/Mathlib.olean" ]; then
  echo "正在获取 Mathlib 预编译缓存..."
  lake exe cache get
fi
echo "Mathlib 环境准备完成。"
