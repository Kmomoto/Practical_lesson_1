#!/usr/bin/env bash
# Минимальная VFS: в архиве один файл hello.txt.
# Запуск: ./scripts/test_vfs_minimal.sh   (интерпретатор: PYTHON=python3.13 ...)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir "$TMP/tree"
echo "hello" > "$TMP/tree/hello.txt"
(cd "$TMP/tree" && zip -q -r "$TMP/minimal.zip" .)

"$PYTHON" "$ROOT/src/main.py" \
    --vfs "$TMP/minimal.zip" \
    --script "$ROOT/scripts/start_minimal.txt"
