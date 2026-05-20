"""Словарь RU-ошибок Whisper → канонические IT-термины (латиница).

Домен: Python backend, инфра, очереди/БД, AI-assisted development.
Источники: практика собесов, Habr (Whisper + русский IT-гибрид), Exa.

Формат WORD_FIXES: (вариант кириллицей, канон).
PHRASE_FIXES: (regex, канон) — длинные фразы, порядок важен.
"""

from __future__ import annotations

# --- Очереди, стриминг, кэш ---
_WORD_MESSAGING: list[tuple[str, str]] = [
    ("кавка", "Kafka"),
    ("кафка", "Kafka"),
    ("кафке", "Kafka"),
    ("кавки", "Kafka"),
    ("кавкану", "Kafka"),
    ("кофта", "Kafka"),  # Habr: «кофта» вместо Kafka на неоднозначном аудио
    ("редис", "Redis"),
    ("редисе", "Redis"),
    ("ребит", "RabbitMQ"),
    ("реббит", "RabbitMQ"),
    ("селери", "Celery"),
    ("целери", "Celery"),
    ("мемкеш", "Memcached"),
    ("консюмер", "consumer"),
    ("консьюмер", "consumer"),
    ("продюсер", "producer"),
    ("топик", "topic"),
    ("офсет", "offset"),
    ("брокер", "broker"),
    ("шардинг", "sharding"),
    ("ретрай", "retry"),
    ("ритри", "retry"),
    ("дедлеттер", "dead letter"),
]

# --- Базы данных ---
_WORD_DATABASES: list[tuple[str, str]] = [
    ("постгрес", "PostgreSQL"),
    ("постгре", "PostgreSQL"),
    ("постгресскл", "PostgreSQL"),
    ("монго", "MongoDB"),
    ("монгодб", "MongoDB"),
    ("кликхаус", "ClickHouse"),
    ("эластик", "Elasticsearch"),
    ("эластиксёрч", "Elasticsearch"),
    ("эластиксерч", "Elasticsearch"),
    ("скуллайт", "SQLite"),
    ("майскул", "MySQL"),
    ("алембик", "Alembic"),
]

# --- Python / web framework ---
_WORD_PYTHON: list[tuple[str, str]] = [
    ("пайтон", "Python"),
    ("пайтест", "pytest"),
    ("асинкио", "asyncio"),
    ("асинхронио", "asyncio"),
    ("фастапи", "FastAPI"),
    ("фаст апи", "FastAPI"),
    ("джанго", "Django"),
    ("фласк", "Flask"),
    ("ювикорн", "uvicorn"),
    ("увикорн", "uvicorn"),
    ("гуникорн", "gunicorn"),
    ("старлет", "Starlette"),
    ("пайдентик", "pydantic"),
    ("пидантик", "pydantic"),
    ("датакласс", "dataclass"),
    ("тайпвар", "TypeVar"),
    ("дженерик", "Generic"),
    ("пикл", "pickle"),
    ("майпай", "mypy"),
    ("рафф", "ruff"),
    ("поэтри", "Poetry"),
    ("виртуаленв", "virtualenv"),
    ("нумпай", "NumPy"),
    ("пандас", "pandas"),
    ("гил", "GIL"),
    ("жил", "GIL"),
    ("гила", "GIL"),
    ("мидлвар", "middleware"),
    ("корутин", "coroutine"),
    ("сабпроцесс", "subprocess"),
    ("мультипроцессинг", "multiprocessing"),
    ("монкипатч", "monkey patch"),
]

# --- Инфра, DevOps ---
_WORD_INFRA: list[tuple[str, str]] = [
    ("докер", "Docker"),
    ("кубернет", "Kubernetes"),
    ("кубернетес", "Kubernetes"),
    ("кубернетис", "Kubernetes"),
    ("энджиникс", "nginx"),
    ("нгинкс", "nginx"),
    ("инжинкс", "nginx"),
    ("хельм", "Helm"),
    ("терраформ", "Terraform"),
    ("ансибл", "Ansible"),
    ("прометеус", "Prometheus"),
    ("графана", "Grafana"),
    ("деплой", "deploy"),
    ("деплоймент", "deployment"),
    ("роллаут", "rollout"),
    ("роллбэк", "rollback"),
    ("хотфикс", "hotfix"),
    ("конфигмап", "ConfigMap"),
    ("стейтфулсет", "StatefulSet"),
]

# --- API, протоколы, безопасность ---
_WORD_API: list[tuple[str, str]] = [
    ("рест", "REST"),
    ("гит", "Git"),
    ("гитхаб", "GitHub"),
    ("гитлаб", "GitLab"),
    ("вебсокет", "WebSocket"),
    ("веб сокет", "WebSocket"),
    ("графкьюэл", "GraphQL"),
    ("оаус", "OAuth"),
    ("оауса", "OAuth"),
    ("жвт", "JWT"),
    ("протобуф", "protobuf"),
    ("протобаф", "protobuf"),
    ("корс", "CORS"),
    ("вебхук", "webhook"),
    ("джейсон", "JSON"),
    ("жсон", "JSON"),
    ("ямл", "YAML"),
    ("ашти ти пи", "HTTP"),
    ("ти эл эс", "TLS"),
    ("орем", "ORM"),
]

# --- AI / LLM / AI-assisted dev ---
_WORD_AI: list[tuple[str, str]] = [
    ("опенэй", "OpenAI"),
    ("опен аи", "OpenAI"),
    ("оупенай", "OpenAI"),
    ("лангчейн", "LangChain"),
    ("лэнгчейн", "LangChain"),
    ("эмбеддинг", "embedding"),
    ("имбеддинг", "embedding"),
    ("токенайзер", "tokenizer"),
    ("файнтюнинг", "fine-tuning"),
    ("промпт", "prompt"),
    ("галлюцинация", "hallucination"),
    ("ллм", "LLM"),
    ("гпт", "GPT"),
    ("клод", "Claude"),
    ("раг", "RAG"),
    ("стриминг", "streaming"),
    ("копилот", "Copilot"),
    ("инференс", "inference"),
    ("трансформер", "transformer"),
]

# --- Общие backend / patterns ---
_WORD_BACKEND: list[tuple[str, str]] = [
    ("бэкенд", "backend"),
    ("бекенд", "backend"),
    ("фронтенд", "frontend"),
    ("кэш", "cache"),
    ("кеш", "cache"),
    ("эйсидай", "ACID"),
    ("эй си дай", "ACID"),
    ("си и си ди", "CI/CD"),
    ("джи ар пи си", "gRPC"),
    ("джиарпи си", "gRPC"),
    ("латенси", "latency"),
    ("таймаут", "timeout"),
    ("дедлок", "deadlock"),
    ("идемпотент", "idempotent"),
    ("репликация", "replication"),
    ("серкит брейкер", "circuit breaker"),
    ("рейт лимит", "rate limit"),
    ("лоад балансер", "load balancer"),
    ("коннекшн пул", "connection pool"),
    ("тред пул", "thread pool"),
    ("ивент луп", "event loop"),
    ("гарбадж коллектор", "garbage collector"),
    ("микросервис", "microservice"),
]

# --- IT-сленг (осторожно: только узнаваемые формы) ---
_WORD_SLANG: list[tuple[str, str]] = [
    ("гошечка", "Go"),
    ("гоша", "Go"),  # «на гоше» — чаще фраза ниже
    ("шарпы", "C#"),
    ("шарп", "C#"),
    ("крудошлёп", "CRUD"),
    ("крудошлеп", "CRUD"),
]

# Порядок категорий при сборке: сленг и длинные фразы не перебивают безопасные слова
WORD_FIXES: list[tuple[str, str]] = (
    _WORD_MESSAGING
    + _WORD_DATABASES
    + _WORD_PYTHON
    + _WORD_INFRA
    + _WORD_API
    + _WORD_AI
    + _WORD_BACKEND
    + _WORD_SLANG
)

# Фразы (regex). Длинные — в начале списка при компиляции.
PHRASE_FIXES: list[tuple[str, str]] = [
    (r"\bзнаешь\s+про\s+поэтому\b", "знаешь про Python"),
    (r"\bрасскаж\w*\s+.*?\s+про\s+поэтому\b", "расскажи что знаешь про Python"),
    (r"\bпро\s+поэтому\b", "про Python"),
    (r"\bпайтон\w*\b", "Python"),
    (r"\bсиквел\s*алхимия\b", "SQLAlchemy"),
    (r"\bтрай\s*[- ]?\s*эксепт\b", "try-except"),
    (r"\bтрай\s*эксепт\b", "try-except"),
    (r"\bэй\s*пи\s*ай\b", "API"),
    (r"\bпул\s+реквест\b", "pull request"),
    (r"\bмерж\s+реквест\b", "merge request"),
    (r"\bпадать\s+в\s+кавк\w*\b", "писать в Kafka"),
    (r"\bна\s+гоше\b", "на Go"),
    (r"\bв\s+прод\b", "в prod"),
    (r"\bна\s+проде\b", "на prod"),
    (r"\bперелить\s+в\s+прод\b", "перелить в prod"),
    (r"\bфайн\s*тюнинг\b", "fine-tuning"),
    (r"\bвекторн\w*\s+бд\b", "vector DB"),
    (r"\bэм\s*ви\s*си\s*си\b", "MVCC"),
]

# Для документации и тестов
GLOSSARY_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "messaging": _WORD_MESSAGING,
    "databases": _WORD_DATABASES,
    "python": _WORD_PYTHON,
    "infra": _WORD_INFRA,
    "api": _WORD_API,
    "ai": _WORD_AI,
    "backend": _WORD_BACKEND,
    "slang": _WORD_SLANG,
}
