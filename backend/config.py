from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    gemini_api_key: str = ""
    groq_api_key: str = ""  # legacy, kept for backward compat
    llm_provider: str = "gemini"  # "gemini" or "groq"
    llm_model: str = "gemini-2.0-flash"

    # Database
    database_url: str = "sqlite:///masteryai.db"
    sqlite_path: str = "masteryai.db"
    redis_url: str = "redis://localhost:6379/0"

    # Data files
    knowledge_graph_path: str = "backend/data/knowledge_graph.json"
    career_roles_path: str = "backend/data/career_roles.json"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Orchestrator
    max_react_steps: int = 5
    max_reasoning_history: int = 10
    max_llm_calls_per_loop: int = 8

    # LLM Client
    retry_delays: list[int] = [1, 2, 4]
    call_timeout: int = 30
    cache_max: int = 1000
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # Examiner
    default_practice_count: int = 2

    # Diagnostic
    max_diagnostic_probes: int = 10
    diagnostic_inferred_score: float = 0.75

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
