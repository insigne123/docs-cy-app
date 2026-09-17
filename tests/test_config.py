"""Normalización de DATABASE_URL para Supabase/Render/Railway."""
from __future__ import annotations

from app.config import Settings


def test_normaliza_esquema_postgres_a_psycopg():
    s = Settings(database_url="postgres://user:pass@db.example.com:5432/postgres")
    assert s.database_url.startswith("postgresql+psycopg://")


def test_agrega_sslmode_a_host_remoto():
    s = Settings(database_url="postgresql://user:pass@db.example.com:5432/postgres")
    assert "sslmode=require" in s.database_url


def test_no_duplica_sslmode_si_ya_viene_incluido():
    s = Settings(database_url="postgresql://user:pass@db.example.com:5432/postgres?sslmode=require")
    assert s.database_url.count("sslmode=") == 1


def test_no_agrega_sslmode_a_localhost():
    s = Settings(database_url="postgresql://user:pass@localhost:5432/postgres")
    assert "sslmode" not in s.database_url


def test_sqlite_no_se_toca():
    s = Settings(database_url="sqlite:///./contratos.db")
    assert s.database_url == "sqlite:///./contratos.db"
