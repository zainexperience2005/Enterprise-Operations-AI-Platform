from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    app_name: str = "Enterprise Operations AI Platform"
    app_env: str = "development"
    debug: bool = True

    database_url: str
    readonly_database_url: str
    checkpoint_database_url: str
    redis_url: str
    qdrant_url: str

    http_timeout_seconds: float = 5.0
    http_max_retries: int = 2

    enterprise_api_url: str = "http://127.0.0.1:8000"
    openai_api_key: str

    langsmith_tracing: bool = True
    langsmith_api_key: str
    langsmith_project: str = "enterprise-operations-ai"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
os.environ["OPENAI_API_KEY"] = settings.openai_api_key

os.environ["LANGSMITH_TRACING"] = str(
    settings.langsmith_tracing
).lower()

os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key

os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project