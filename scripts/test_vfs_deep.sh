#!/usr/bin/env bash
# VFS с глубокой вложенностью (до 4 уровней: docs/manual/chapter1/intro.txt),
# пустым каталогом projects/empty и записями о каталогах в архиве.
# Выполняет общий стартовый скрипт start_all.txt (он заканчивается командой exit,
# поэтому окно закроется само; чтобы посмотреть результат, уберите exit в конце).
# Запуск: ./scripts/test_vfs_deep.sh   (интерпретатор: PYTHON=python3.13 ...)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
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
    --script "$ROOT/scripts/start_all.txt"
