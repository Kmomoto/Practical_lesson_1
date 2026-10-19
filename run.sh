#!/usr/bin/env bash
# Запуск эмулятора. Все аргументы (--vfs, --script) передаются дальше.
exec python3 "$(dirname "$0")/src/main.py" "$@"
