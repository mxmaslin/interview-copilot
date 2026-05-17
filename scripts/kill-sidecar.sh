#!/usr/bin/env bash
# Зависший copilot после force quit Cursor / kill -9
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/data/sidecar.lock"

if [[ -f "$LOCK" ]]; then
  PID="$(cat "$LOCK" 2>/dev/null || true)"
  if [[ -n "${PID:-}" ]]; then
    kill -9 "$PID" 2>/dev/null || true
    echo "killed sidecar PID=$PID"
  fi
fi

pkill -9 -f "$ROOT/.venv.*copilot" 2>/dev/null || true
pkill -9 -f "agent.mjs" 2>/dev/null || true
rm -f "$LOCK"
echo "lock removed"
