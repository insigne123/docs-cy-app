"""Configuración de la aplicación (leída de variables de entorno / .env)."""
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SQLite por defecto para desarrollo/pruebas. En producción: PostgreSQL.
    database_url: str = "sqlite:///./contratos.db"
    echo_sql: bool = False

    # Autenticación. Desactivada por defecto (uso local). Activar en producción.
    auth_required: bool = False
    secret_key: str = "dev-inseguro-cambiar-en-produccion"

    @field_validator("database_url")
    @classmethod
    def _normalizar_database_url(cls, v: str) -> str:
        """Adapta las URLs que entregan Render/Railway/Heroku (postgres://, postgresql://)
        al driver psycopg (v3) que usa este proyecto."""
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://") and "+psycopg" not in v:
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v


settings = Settings()
