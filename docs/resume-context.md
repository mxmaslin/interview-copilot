# Резюме в контексте Copilot

Агент и sidecar могут опираться на **`context/resume.md`** при ответах на интервью (реальный опыт, стек, проекты).

## Источник

Актуальная ссылка: `context/resume.hh-url`  
Сейчас: https://hh.ru/resume/YOUR_HH_RESUME_ID

Публичная страница hh.ru **без входа не читается** (SPA + API `403 forbidden`). Нужен один из способов ниже.

## Exa vs API hh.ru

| Способ | Когда работает | Для твоего резюме |
|--------|----------------|-------------------|
| **API hh.ru** + `HH_ACCESS_TOKEN` | OAuth соискателя ([dev.hh.ru](https://dev.hh.ru)), `GET /resumes/{id}` | **Рекомендуется** — полный JSON, стабильно |
| **Exa** (`EXA_API_KEY`, `--exa`) | Публичная страница, которую Exa может скачать | Часто **нет**: hh — SPA, таймаут/логин; закрытое резюме — 403 |
| **Копипаст** | Всегда | Самый простой разовый вариант |

Exa в Cursor (MCP `web_fetch_exa`) — то же ограничение: на твоей ссылке был `CRAWL_LIVECRAWL_TIMEOUT`.

**Итог:** Exa — запасной костыль для открытых URL; **автосинхронизация = hh OAuth**, не Exa.

## Обновить `context/resume.md`

### Быстро (копипаст)

1. Открой резюме на hh.ru в браузере (ты залогинен).
2. Выдели весь текст → скопируй.
3. В терминале из корня репозитория:

```bash
pbpaste | python scripts/import-resume.py
```

### Из файла

Экспорт / сохранение с hh → `resume.txt`, затем:

```bash
python scripts/import-resume.py -f resume.txt
```

### Через API hh.ru (рекомендуется для автообновления)

1. Зарегистрируй приложение на [dev.hh.ru](https://dev.hh.ru) (тип «для соискателей»).
2. [Авторизация пользователя](https://github.com/hhru/api/blob/master/docs/authorization_for_user.md): redirect → `code` → `access_token`.
3. Токен в `.env` (не коммить):

```bash
HH_ACCESS_TOKEN=...
python scripts/import-resume.py
```

Скрипт дергает `GET https://api.hh.ru/resumes/{id}` и собирает `context/resume.md`.

### Через Exa (эксперимент)

Если резюме на hh **видно всем в интернете** и Exa его тянет:

```bash
EXA_API_KEY=... python scripts/import-resume.py --exa
```

Или в Cursor: MCP Exa → `web_fetch_exa` по URL из `context/resume.hh-url`.

## Редакция для hh.ru

Готовый текст для копипаста в поля hh: **`context/resume-for-hh.md`** (блоки «О себе», опыт, навыки).  
Агент Copilot читает **`context/resume.md`** — держи оба файла в синхроне после правок.

## В Cursor

В чате агента: `@context/resume.md` — или правило Copilot уже ссылается на файл.

## Приватность

`context/resume.md` может содержать ПДн. Не пушь в публичный репозиторий без необходимости (можно добавить в `.gitignore`).
