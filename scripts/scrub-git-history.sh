#!/usr/bin/env bash
# Однократно перед первым публичным push, если в истории был context/resume.hh-url
# с реальным ID или URL резюме.
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

REPL_FILE="${COPILOT_SCRUB_REPLACEMENTS_FILE:-${ROOT}/context/scrub-replacements.local}"
if [[ ! -f "${REPL_FILE}" ]]; then
  echo "Нет файла замен: ${REPL_FILE}" >&2
  echo "Скопируй: cp context/scrub-replacements.example context/scrub-replacements.local" >&2
  echo "Формат строк: literal==>replacement (см. context/scrub-replacements.example)" >&2
  exit 1
fi

REPL="$(mktemp)"
trap 'rm -f "${REPL}"' EXIT
grep -v '^[[:space:]]*#' "${REPL_FILE}" | grep -v '^[[:space:]]*$' >"${REPL}" || true
if [[ ! -s "${REPL}" ]]; then
  echo "Файл замен пуст: ${REPL_FILE}" >&2
  exit 1
fi

echo "[scrub] Удаляю context/resume.hh-url из всей истории (если был в коммитах)..."
if git log --all --oneline -- "context/resume.hh-url" | grep -q .; then
  git filter-repo --path context/resume.hh-url --invert-paths --force
else
  echo "[scrub] context/resume.hh-url в истории не найден, пропуск."
fi

echo "[scrub] Заменяю строки из ${REPL_FILE} ..."
git filter-repo --replace-text "${REPL}" --force

rm -f "${REPL}"
trap - EXIT
echo "[scrub] Готово. Проверь: git log -p | head"
echo "  pytest sidecar/tests/test_repo_hygiene.py"
echo "При push: git push --force-with-lease (история переписана)."
