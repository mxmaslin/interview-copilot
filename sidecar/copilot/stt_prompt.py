from __future__ import annotations

from .config import whisper_initial_prompt, whisper_prompt_mode

# Короткий prompt — без перечисления брендов (не эхоится на тишине).
_GENERAL = (
    "Русская разговорная речь. "
    "Технические термины и имена продуктов — латиницей, не кириллицей."
)

# Собес / live coding: контекст IT без списка Kafka, Redis, …
_TECH = (
    "Техническое интервью, русская речь. "
    "Библиотеки, протоколы, БД, очереди, инфраструктура — латиницей (English letters)."
)

# Максимум подсказок латиницей (длинный prompt, только режим interview).
_INTERVIEW = (
    "Техническое интервью, русская речь, IT-термины латиницей: "
    "Python, GIL, asyncio, event loop, coroutine, generator, decorator, "
    "thread, process, memory, garbage collector, "
    "PostgreSQL, Postgres, Redis, SQL, index, B-tree, transaction, ACID, "
    "isolation level, MVCC, replication, sharding, "
    "Docker, container, Kubernetes, pod, deployment, "
    "REST, API, HTTP, JSON, gRPC, WebSocket, "
    "FastAPI, Django, Flask, SQLAlchemy, ORM, migration, "
    "pytest, unit test, integration test, CI/CD, Git, pull request, "
    "latency, throughput, cache, queue, Kafka, Celery, "
    "microservices, monolith, backend, middleware, load balancer, "
    "CAP theorem, eventual consistency, single point of failure."
)


def interview_whisper_prompt() -> str:
    custom = whisper_initial_prompt()
    if custom:
        return custom
    mode = whisper_prompt_mode()
    if mode in ("general", "casual", "dialog"):
        return _GENERAL
    if mode in ("tech", "it", "mixed"):
        return _TECH
    return _INTERVIEW
