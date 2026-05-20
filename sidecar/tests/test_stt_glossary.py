from __future__ import annotations

import pytest

import copilot.config as config
from copilot.stt_glossary import apply_glossary_fixes, glossary_entry_count
from copilot.stt_glossary_terms import GLOSSARY_CATEGORIES, PHRASE_FIXES, WORD_FIXES


@pytest.fixture
def glossary_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("WHISPER_GLOSSARY_FIXES", "1")


def test_glossary_entry_count() -> None:
    assert glossary_entry_count() == len(WORD_FIXES) + len(PHRASE_FIXES)
    assert len(GLOSSARY_CATEGORIES) >= 6


def test_glossary_gil_redis(glossary_on: None) -> None:
    assert apply_glossary_fixes("Расскажи про гил и редис") == (
        "Расскажи про GIL и Redis"
    )


def test_glossary_kafka(glossary_on: None) -> None:
    assert apply_glossary_fixes("Расскажи, что знаешь про кавка") == (
        "Расскажи, что знаешь про Kafka"
    )


def test_glossary_kafka_coat_habr(glossary_on: None) -> None:
    assert apply_glossary_fixes("очередь кофта") == "очередь Kafka"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("работал с постгрес и ребит", "работал с PostgreSQL и RabbitMQ"),
        ("стек фаст апи плюс селери", "стек FastAPI плюс Celery"),
        ("трай эксепт в пайтоне", "try-except в Python"),
        ("пул реквест в гитхаб", "pull request в GitHub"),
        ("эмбеддинг для раг", "embedding для RAG"),
        ("крудошлёп в REST API", "CRUD в REST API"),
        ("деплой в прод через кубернетес", "deploy в prod через Kubernetes"),
        ("опиши оаус и жвт", "опиши OAuth и JWT"),
    ],
)
def test_glossary_param_samples(glossary_on: None, raw: str, expected: str) -> None:
    assert apply_glossary_fixes(raw) == expected


def test_glossary_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("WHISPER_GLOSSARY_FIXES", "0")
    text = "про гил"
    assert apply_glossary_fixes(text) == text
