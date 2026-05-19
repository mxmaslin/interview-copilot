#!/usr/bin/env bash
# Создать github.com/<you>/copilot и запушить main.
# Требует: gh auth login
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v gh >/dev/null 2>&1; then
  echo "Установи GitHub CLI: brew install gh" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Сначала войди в GitHub: gh auth login" >&2
  exit 1
fi

VISIBILITY="${COPILOT_GITHUB_VISIBILITY:-private}"

if git remote get-url origin >/dev/null 2>&1; then
  echo "[publish] remote origin уже есть, push..."
  git push -u origin main
  gh repo view --web 2>/dev/null || true
  exit 0
fi

echo "[publish] Создаю репозиторий copilot (${VISIBILITY})..."
gh repo create copilot \
  --"${VISIBILITY}" \
  --source=. \
  --remote=origin \
  --description="macOS menubar copilot for technical interviews (Cursor + STT)" \
  --push

echo "[publish] Готово:"
gh repo view --json url -q .url
