# STT text fixtures (фаза 2)

Ожидаемое поведение покрыто unit-тестами в `test_stt_filter.py`, `test_stt_segment.py`, `test_transcript.py`.

| Файл | Смысл |
|------|--------|
| `silence_tech_echo.txt` | Эхо Whisper prompt на тишине → `is_stt_hallucination` |
| `complete_question.txt` | Нормальный вопрос → не фильтруется |
| `incomplete_tail.txt` | Обрезанный хвост → `is_incomplete_self_utterance` |

Аудио `.wav` — опционально, локально с `@pytest.mark.audio` (не в CI по умолчанию).
