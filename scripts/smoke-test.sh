#!/usr/bin/env bash
# Быстрая проверка Copilot без menubar.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

echo "== pytest =="
pytest sidecar/tests -q

echo "== transcript =="
python -c "
from copilot.transcript import append_line, last_interviewer_line
print(append_line('interviewer', '[SMOKE] ok'))
print('last:', last_interviewer_line())
"

echo "== lock =="
python -c "
from copilot.instance import SidecarLock
l = SidecarLock()
assert l.acquire()
l.release()
print('lock ok')
"

if python -c "from copilot.config import cursor_api_key; exit(0 if cursor_api_key() else 1)"; then
  echo "== SDK start (may take ~1 min) =="
  python -c "from copilot.cursor_bridge import start_session; print(start_session())"
else
  echo "== SDK: skip (no CURSOR_API_KEY in .env) =="
fi

echo "== done =="
