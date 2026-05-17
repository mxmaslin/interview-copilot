#!/usr/bin/env zsh
# Запуск menubar sidecar из venv проекта (обходит pyenv shims).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/.venv/bin/copilot" "$@"
