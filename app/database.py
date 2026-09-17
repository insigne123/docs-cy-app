"""Motor y sesión de base de datos."""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base

_is_sqlite = settings.database_url.startswith("sqlite")
# `prepare_threshold=None` desactiva las sentencias preparadas del lado del servidor:
# necesario si se conecta a través del pooler de Supabase (Supavisor/pgbouncer en modo
# "transaction"), que no sostiene el estado de sesión entre consultas. No afecta a una
# conexión directa a Postgres.
_connect_args = {"check_same_thread": False} if _is_sqlite else {"prepare_threshold": None}

engine = create_engine(settings.database_url, echo=settings.echo_sql, connect_args=_connect_args, future=True)


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_fk_pragma(dbapi_connection, connection_record):  # pragma: no cover
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def crear_todo() -> None:
    """Crea todas las tablas (Etapa 1). En producción se migrará con Alembic (Etapa 2)."""
    import app.models  # noqa: F401  asegura el registro de todos los modelos

    Base.metadata.create_all(engine)


def get_session():
    """Dependencia estilo FastAPI: entrega una sesión y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
