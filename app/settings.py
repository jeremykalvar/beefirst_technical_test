from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_env: str = "dev"
    log_level: str = "INFO"

    # Infra
    database_url: str = "postgresql://app:app@db:5432/app"
    redis_url: str = "redis://redis:6379/0"
    smtp_base_url: str = "http://smtp-mock:8025"

    # Security / policies
    bcrypt_rounds: int = 12
    code_ttl_seconds: int = 60
    code_attempts: int = 5
    resend_throttle_seconds: int = 60

    # Worker
    outbox_poll_interval_ms: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
