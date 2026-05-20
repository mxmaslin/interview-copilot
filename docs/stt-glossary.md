# Словарь STT: Python backend и AI-assisted development

Whisper на русскоязычных собесах часто пишет IT-термины **кириллицей** или подменяет их бытовыми словами («**кавка**» / «**кофта**» вместо **Kafka**). Copilot исправляет это **после** распознавания, без списка брендов в `initial_prompt` (чтобы не эхоилось на тишине).

## Как включено в коде

| Файл | Роль |
|------|------|
| [`sidecar/copilot/stt_glossary_terms.py`](../sidecar/copilot/stt_glossary_terms.py) | Таблица пар «ошибка → канон» по категориям |
| [`sidecar/copilot/stt_glossary.py`](../sidecar/copilot/stt_glossary.py) | Компиляция regex и `apply_glossary_fixes()` |
| `transcript.py`, `stt_live.py` | Glossary на финале и в live-sanitize |

```env
WHISPER_GLOSSARY_FIXES=1   # по умолчанию в .env.example
```

Добавление термина: пара в `stt_glossary_terms.py` → `pytest sidecar/tests/test_stt_glossary.py`.

## Откуда взяты формулировки

- [Habr: почему Whisper плохо слышит русских айтишников](https://habr.com/ru/articles/1026778/) — гибрид RU+EN, «кофта»/Kafka, try-except, retry, сленг (гошечка, крудошлёп).
- Практика rolling STT на собесах (copilot).
- Exa: обсуждения Whisper + RU tech speech, `WHISPER_INITIAL_PROMPT` с English tech terms.

## Категории (краткий указатель)

### Очереди и стриминг

| Часто слышится (RU) | Канон |
|---------------------|--------|
| кавка, кафка, кофта, кавкану, **кавказ**, **кавкад**, **такавка** | Kafka |
| `про кавк…` (regex) | `про Kafka` |
| редис | Redis |
| ребит, реббит | RabbitMQ |
| селери, целери | Celery |
| ритри, ретрай | retry |
| консюмер, продюсер, топик, офсет, брокер | consumer, producer, topic, offset, broker |

### Базы данных

| RU | Канон |
|----|--------|
| постгрес, постгре | PostgreSQL |
| монго, монгодб | MongoDB |
| кликхаус | ClickHouse |
| эластик, эластиксёрч | Elasticsearch |
| алембик | Alembic |

### Python / web

| RU | Канон |
|----|--------|
| пайтон, поэтому (в «про поэтому») | Python |
| асинкио | asyncio |
| фаст апи, фастапи | FastAPI |
| джанго, фласк | Django, Flask |
| ювикорн, гуникорн | uvicorn, gunicorn |
| пайдентик, пидантик | pydantic |
| сиквел алхимия (фраза) | SQLAlchemy |
| гил, жил | GIL |
| пайтест | pytest |
| майпай, рафф, поэтри | mypy, ruff, Poetry |

### Инфра

| RU | Канон |
|----|--------|
| докер | Docker |
| кубернет(ес\|ис) | Kubernetes |
| энджиникс, нгинкс | nginx |
| терраформ, хельм, ансибл | Terraform, Helm, Ansible |
| прометеус, графана | Prometheus, Grafana |
| в прод, на проде (фразы) | prod |

### API и протоколы

| RU | Канон |
|----|--------|
| рест | REST |
| вебсокет | WebSocket |
| графкьюэл | GraphQL |
| оаус, жвт | OAuth, JWT |
| джейсон, ямл | JSON, YAML |
| трай эксепт (фраза) | try-except |
| пул реквест, мерж реквест | pull request, merge request |

### AI / LLM / dev tools

| RU | Канон |
|----|--------|
| опен аи, оупенай | OpenAI |
| лангчейн | LangChain |
| эмбеддинг, токенайзер, файнтюнинг | embedding, tokenizer, fine-tuning |
| ллм, гпт, клод, раг | LLM, GPT, Claude, RAG |
| копилот | Copilot |

### Сленг (узкие замены)

| RU | Канон | Риск |
|----|--------|------|
| гошечка, «на гоше» | Go | только узнаваемые формы |
| шарпы | C# | не трогаем «плюсы и минусы» |
| крудошлёп | CRUD | — |
| падать в кавку | писать в Kafka | фраза |

**Намеренно не в словаре:** «три»→retry (ложные срабатывания), «жаба»→Java, «плюсы»→C++.

## Связь с Whisper prompt

| `WHISPER_PROMPT_MODE` | Подсказка |
|------------------------|-----------|
| `tech` | IT-контекст, латиница, **без** перечисления брендов |
| `interview` | Длинный список латиницей (может эхоиться на тишине) |
| `general` | HR / общий созвон |

Glossary и prompt **дополняют** друг друга: prompt снижает ошибки на decode, glossary чинит остаток в тексте.

## Расширение словаря

1. Поймать сырую фразу в live-терминале или **CP → Показать диалог** (RAM).
2. Добавить в нужную секцию `stt_glossary_terms.py` (слово — в `WORD_*`, фраза — в `PHRASE_FIXES`).
3. Тест в `test_stt_glossary.py` одной строкой.
4. При необходимости — строка в этот doc (таблица категории).

Полный машинный список: `python -c "from copilot.stt_glossary_terms import WORD_FIXES, PHRASE_FIXES; print(len(WORD_FIXES), len(PHRASE_FIXES))"` из каталога `sidecar/`.

См. также: [voice-pipeline.md](voice-pipeline.md), [audio-setup.md](audio-setup.md).
