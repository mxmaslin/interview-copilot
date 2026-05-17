#!/usr/bin/env zsh
# Активация project venv; bin/ и .venv/bin — раньше pyenv shims.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export VIRTUAL_ENV="${ROOT}/.venv"
export PATH="${ROOT}/bin:${ROOT}/.venv/bin:${PATH}"
# shellcheck source=/dev/null
source "${ROOT}/.venv/bin/activate"
unset PYENV_VERSION 2>/dev/null || true
hash -r 2>/dev/null || rehash 2>/dev/null || true
echo "python: $(which python)"
echo "copilot: $(whence -p copilot 2>/dev/null || which copilot)"
