from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise Operations AI Platform"
    app_env: str = "development"
    debug: bool = True

    database_url: str
    redis_url: str
    qdrant_url: str

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