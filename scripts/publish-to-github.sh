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

REPO_SLUG="${COPILOT_GITHUB_REPO:-mxmaslin/interview-copilot}"
REMOTE_URL="https://github.com/${REPO_SLUG}.git"

if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "${REMOTE_URL}"
else
  git remote set-url origin "${REMOTE_URL}"
fi

echo "[publish] origin -> ${REMOTE_URL}"
gh auth setup-git
git push -u origin main

echo "[publish] Готово:"
gh repo view "${REPO_SLUG}" --json url -q .url
