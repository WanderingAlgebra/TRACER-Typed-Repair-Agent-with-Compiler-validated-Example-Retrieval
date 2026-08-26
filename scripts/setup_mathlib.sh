#!/usr/bin/env bash
set -euo pipefail

PROJECT="${1:-$(dirname "$0")/../mathlib_project}"
if [[ -z "${MATHLIB_CACHE_DIR:-}" ]]; then
  if [[ -n "${XDG_CACHE_HOME:-}" ]]; then
    MATHLIB_CACHE_DIR="${XDG_CACHE_HOME}/mathlib"
  elif [[ -n "${HOME:-}" ]]; then
    MATHLIB_CACHE_DIR="${HOME}/.cache/mathlib"
  else
    echo "HOME or MATHLIB_CACHE_DIR is required" >&2
    exit 2
  fi
  export MATHLIB_CACHE_DIR
fi
mkdir -p "$MATHLIB_CACHE_DIR"

cd "$PROJECT"
echo "Syncing Mathlib dependencies..."
lake update
if [[ ! -f ".lake/packages/mathlib/.lake/build/lib/lean/Mathlib.olean" ]]; then
  echo "Fetching the Mathlib precompiled cache..."
  lake exe cache get
fi
echo "Mathlib environment is ready."
