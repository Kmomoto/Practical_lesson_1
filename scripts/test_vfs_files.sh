#!/usr/bin/env bash
# VFS с несколькими файлами: текстовые и двоичный файл, один вложенный каталог.
# Архив создаётся с ключом -D, то есть БЕЗ записей о каталогах: каталог docs
# существует только как часть путей docs/a.txt и docs/b.txt.
# Запуск: ./scripts/test_vfs_files.sh   (интерпретатор: PYTHON=python3.13 ...)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/tree/docs"
echo "заметки" > "$TMP/tree/notes.txt"
printf '\x00\x01\x02\xff' > "$TMP/tree/data.bin"
echo "файл a" > "$TMP/tree/docs/a.txt"
echo "файл b" > "$TMP/tree/docs/b.txt"
(cd "$TMP/tree" && zip -q -r -D "$TMP/files.zip" .)

"$PYTHON" "$ROOT/src/main.py" \
    --vfs "$TMP/files.zip" \
    --script "$ROOT/scripts/start_files.txt"
