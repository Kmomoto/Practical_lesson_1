#!/usr/bin/env bash
# Этап 5: VFS для проверки rmdir и mv (пустые каталоги, цепочки, конфликты имён).
# Изменения происходят только в памяти эмулятора: архив не меняется.
# Запуск: ./scripts/test_vfs_stage5.sh [скрипт]   (интерпретатор: PYTHON=python3.13 ...)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
SCRIPT="${1:-$ROOT/scripts/start_stage5.txt}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

T="$TMP/tree"
mkdir -p "$T/docs/manual" "$T/archive" "$T/empty1" "$T/empty2" \
    "$T/trash/old/cache" "$T/deep/inner" "$T/full" \
    "$T/a/x" "$T/b/x" "$T/inbox" "$T/p/q" "$T/r/q"
echo "корневой файл" > "$T/readme.txt"
echo "заметки" > "$T/notes.txt"
echo "руководство" > "$T/docs/guide.txt"
echo "оглавление" > "$T/docs/manual/index.txt"
echo "файл" > "$T/deep/f.txt"
echo "файл" > "$T/full/file.txt"
echo "y" > "$T/a/x/y.txt"
echo "z" > "$T/b/x/z.txt"
echo "письмо a" > "$T/inbox/a.txt"
echo "письмо b" > "$T/inbox/b.txt"
(cd "$T" && zip -q -r "$TMP/stage5.zip" .)

"$PYTHON" "$ROOT/src/main.py" --vfs "$TMP/stage5.zip" --script "$SCRIPT"
