#!/usr/bin/env bash
# Однократно перед первым публичным push, если в истории был context/resume.hh-url
# с реальным ID или URL резюме в docs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "Установи: pip install git-filter-repo" >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Не git-репозиторий: $ROOT" >&2
  exit 1
fi

REPL="$(mktemp)"
trap 'rm -f "$REPL"' EXIT
cat >"$REPL" <<'EOF'
YOUR_HH_RESUME_ID==>YOUR_HH_RESUME_ID
EOF

echo "[scrub] Удаляю context/resume.hh-url из всей истории…"
git filter-repo --path context/resume.hh-url --invert-paths --force

echo "[scrub] Заменяю старый resume ID в оставшихся коммитах…"
git filter-repo --replace-text "$REPL" --force

rm -f "$REPL"
echo "[scrub] Готово. Проверь: git log -p | head   и   pytest sidecar/tests/test_repo_hygiene.py"
echo "При push: git push --force-with-lease (история переписана)."
