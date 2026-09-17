"""Configuración de la aplicación (leída de variables de entorno / .env)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SQLite por defecto para desarrollo/pruebas. En producción: PostgreSQL.
    database_url: str = "sqlite:///./contratos.db"
    echo_sql: bool = False

    # Autenticación. Desactivada por defecto (uso local). Activar en el servidor de red.
    auth_required: bool = False
    secret_key: str = "dev-inseguro-cambiar-en-produccion"


settings = Settings()
