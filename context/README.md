# Контекст для интервью

| Файл | Назначение |
|------|------------|
| `resume.md` | Резюме / опыт — **`@context/resume.md`** в Cursor |
| `resume.hh-url` | Ваш URL hh.ru (локально, **не в git**) |
| `resume.hh-url.example` | Шаблон URL (в git) |
| `resume.example.md` | Пример структуры (в git) |
| `resume-for-hh.md` | Текст для hh (локально, gitignored) |
| `vacancy.md` | Описание вакансии (опционально) |

## Обновить резюме с hh.ru

```bash
pbpaste | python scripts/import-resume.py
```

См. [docs/resume-context.md](../docs/resume-context.md).
