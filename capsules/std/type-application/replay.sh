#!/usr/bin/env sh
set -eu
capsule_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$capsule_dir
while [ "$repo_root" != "/" ] && [ ! -f "$repo_root/leancapsule/__main__.py" ]; do
  repo_root=$(dirname -- "$repo_root")
done
if [ -f "$repo_root/leancapsule/__main__.py" ]; then
  cd "$repo_root"
fi
exec python -m leancapsule replay "$capsule_dir"
