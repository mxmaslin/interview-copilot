# Безопасность и публикация репозитория

## Что не коммитить

| Путь / файл | Содержимое |
|-------------|------------|
| `.env` | API-ключи, токены Telegram, hh.ru |
| `context/resume.md`, `context/resume-for-hh.md` | ПДн, опыт, контакты |
| `context/resume.hh-url` | Прямая ссылка на ваше резюме hh.ru |
| `context/forbidden-patterns.local` | Ваши подстроки для локальной проверки ПДн |
| `context/scrub-replacements.local` | Замены для `scrub-git-history.sh` |
| `context/vacancy.md` | Личные заметки по вакансии |
| `data/*`, `data/sessions/` | Транскрипты, архивы сессий с ответами ИИ, agent-state |
| `резюме*.pdf` | PDF резюме |
| `.playwright-mcp/` | Логи браузера с URL |

Шаблоны: `.env.example`, `context/resume.example.md`, `context/resume.hh-url.example`, `context/forbidden-patterns.example`, `context/scrub-replacements.example`.

## Перед первым push на GitHub

1. Скопируй конфиг локально:
   ```bash
   cp .env.example .env
   cp context/resume.hh-url.example context/resume.hh-url
   cp context/forbidden-patterns.example context/forbidden-patterns.local
   ```
2. Заполни `.env` и `context/resume.md` (остаются только у тебя).
3. Если репозиторий **уже коммитился** с личными данными:
   ```bash
   cp context/scrub-replacements.example context/scrub-replacements.local
   pip install git-filter-repo
   ./scripts/scrub-git-history.sh
   ```
4. Проверка:
   ```bash
   cd sidecar && pytest tests/test_repo_hygiene.py -q
   git grep -E 'HH_ACCESS_TOKEN=sk|TELEGRAM_BOT_TOKEN=[0-9]|api\.hh\.ru/resume/[a-f0-9]{20,}' || echo OK
   ```

В CI (GitHub Actions) автоматически: `test_repo_hygiene` и полный `pytest`.

## Скомпрометированный ключ

Отзови токен в кабинете провайдера (Cursor, DeepSeek, OpenAI, Telegram BotFather, hh.ru) и выпусти новый.

## Отчёт об уязвимости

Для личного репозитория: issues на GitHub или личный контакт владельца.
