from __future__ import annotations

from .config import whisper_initial_prompt

# Плотный список EN-терминов в латинице — Whisper использует prompt как «образец» вывода.
_DEFAULT = (
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
    return _DEFAULT
