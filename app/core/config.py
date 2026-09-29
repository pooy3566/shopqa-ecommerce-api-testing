from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

# Known placeholder keys that must never sign real tokens (CWE-798).
_PLACEHOLDER_SECRETS = {
    "your-secret-key-change-in-production",
    "change-me-in-production",
    "changeme",
    "secret",
    "",
}


class Settings(BaseSettings):
    """Application settings and configuration."""

    # Project Information
    PROJECT_NAME: str = "E-Commerce API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ecommerce_db"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/ecommerce_db"

    # JWT Configuration
    # SECRET_KEY has no default on purpose. The app must refuse to start rather
    # than boot with a guessable signing key (CWE-798). Generate one with:
    #   python -c "import secrets; print(secrets.token_urlsafe(48))"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_ISSUER: str = "ecommerce-api"
    JWT_AUDIENCE: str = "ecommerce-api-clients"

    # CORS: explicit allowlist, never "*" alongside credentials (CWE-942).
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def _reject_weak_secret(cls, v: str) -> str:
        if v in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "SECRET_KEY is a known placeholder. Generate one with "
                '`python -c "import secrets; print(secrets.token_urlsafe(48))"`'
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v


settings = Settings()
