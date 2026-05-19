# Безопасность и публикация репозитория

## Что не коммитить

| Путь / файл | Содержимое |
|-------------|------------|
| `.env` | API-ключи, токены Telegram, hh.ru |
| `context/resume.md`, `context/resume-for-hh.md` | ПДн, опыт, контакты |
| `context/resume.hh-url` | Прямая ссылка на ваше резюме hh.ru |
| `context/vacancy.md` | Личные заметки по вакансии |
| `data/*` | Транскрипты интервью, ответы, agent-state |
| `резюме*.pdf` | PDF резюме |
| `.playwright-mcp/` | Логи браузера с URL |

Шаблоны: `.env.example`, `context/resume.example.md`, `context/resume.hh-url.example`.

## Перед первым push на GitHub

1. Скопируй конфиг локально:
   ```bash
   cp .env.example .env
   cp context/resume.hh-url.example context/resume.hh-url
   ```
2. Заполни `.env` и `context/resume.md` (остаются только у тебя).
3. Если репозиторий **уже коммитился** с личными данными — очисти историю:
   ```bash
   pip install git-filter-repo
   ./scripts/scrub-git-history.sh
   ```
4. Проверка:
   ```bash
   cd sidecar && pytest tests/test_repo_hygiene.py -q
   git grep -E 'HH_ACCESS_TOKEN=sk|TELEGRAM_BOT_TOKEN=[0-9]|api\.hh\.ru/resume/[a-f0-9]{20,}' || echo OK
   ```

## Скомпрометированный ключ

Отзови токен в кабинете провайдера (Cursor, DeepSeek, OpenAI, Telegram BotFather, hh.ru) и выпусти новый.

## Отчёт об уязвимости

Для личного репозитория: issues на GitHub или личный контакт владельца.
