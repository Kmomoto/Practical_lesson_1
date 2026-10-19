#!/usr/bin/env bash
# VFS с глубокой вложенностью (до 4 уровней: docs/manual/chapter1/intro.txt),
# пустым каталогом projects/empty и записями о каталогах в архиве.
# Выполняет стартовый скрипт эмулятора: по умолчанию start_all.txt (этапы 1-3,
# заканчивается командой exit, поэтому окно закроется само; чтобы посмотреть
# результат, уберите exit в конце) или скрипт, указанный первым аргументом.
# Запуск: ./scripts/test_vfs_deep.sh [скрипт]   (интерпретатор: PYTHON=python3.13 ...)
# Этап 4:  ./scripts/test_vfs_deep.sh scripts/start_stage4.txt
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
SCRIPT="${1:-$ROOT/scripts/start_all.txt}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

T="$TMP/tree"
mkdir -p "$T/docs/manual/chapter1" "$T/projects/alpha/src" "$T/projects/empty"
echo "корневой файл" > "$T/readme.txt"
echo "руководство" > "$T/docs/guide.txt"
echo "оглавление" > "$T/docs/manual/index.txt"
echo "введение" > "$T/docs/manual/chapter1/intro.txt"
echo "заметки" > "$T/docs/manual/chapter1/notes.txt"
echo "int main() { return 0; }" > "$T/projects/alpha/src/main.c"
(cd "$T" && zip -q -r "$TMP/deep.zip" .)

"$PYTHON" "$ROOT/src/main.py" \
    --vfs "$TMP/deep.zip" \
    --script "$SCRIPT"
