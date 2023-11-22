from typing import Any, Dict
from pathlib import Path

from pydantic import BaseSettings, FilePath, PostgresDsn, validator


class _Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    PROJECT_NAME: str = "Barcode API"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # DB
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: PostgresDsn | None = None

    # OIDC
    OIDC_CLIENT_ID: str
    OIDC_BASE_AUTHORIZATION_SERVER_URI: str
    OIDC_ISSUER: str
    OIDC_SIGNATURE_CACHE_TTL: int
    OIDC_JWT_LEEWAY: float = 5.0

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: str | None, values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            # Required +psycopg in order to use psycopg3
            scheme="postgresql+psycopg",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER") or "",
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )

    # Scraper
    BROWSER_PATH: FilePath = Path("/usr/bin/chromium")

    class Config:
        case_sensitive = True
        env_file = ".env"


# Also why is mypy complaining about this? It works fine.
settings = _Settings()  # type: ignore


def get_database_url() -> str:
    return str(settings.SQLALCHEMY_DATABASE_URI)
