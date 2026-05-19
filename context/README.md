# Контекст для интервью

| Файл | Назначение |
|------|------------|
| `resume.md` | Резюме / опыт — **`@context/resume.md`** в Cursor |
| `resume.hh-url` | Ссылка на актуальное резюме hh.ru |
| `resume.example.md` | Пример структуры (в git) |
| `vacancy.md` | Описание вакансии (опционально) |

## Обновить резюме с hh.ru

```bash
pbpaste | python scripts/import-resume.py
```

См. [docs/resume-context.md](../docs/resume-context.md).
