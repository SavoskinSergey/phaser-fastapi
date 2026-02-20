import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Конфигурация приложения."""
    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production-use-env")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/one_day"
    )

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
