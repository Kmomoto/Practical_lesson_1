#!/usr/bin/env bash
# Ошибки загрузки VFS: архива нет, файл не является ZIP, параметр --vfs не указан.
# Эмулятор запускается три раза подряд; закройте окно, чтобы перейти к следующему.
# Запуск: ./scripts/test_vfs_errors.sh   (интерпретатор: PYTHON=python3.13 ...)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

SCRIPT="$ROOT/scripts/start_errors.txt"
echo "not a zip" > "$TMP/broken.zip"

echo "== 1. архив не существует =="
"$PYTHON" "$ROOT/src/main.py" --vfs "$TMP/no_such.zip" --script "$SCRIPT"

echo "== 2. файл не является ZIP-архивом =="
"$PYTHON" "$ROOT/src/main.py" --vfs "$TMP/broken.zip" --script "$SCRIPT"

echo "== 3. параметр --vfs не указан =="
"$PYTHON" "$ROOT/src/main.py" --script "$SCRIPT"
