"""Construcción de la aplicación FastAPI."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.deps import guardia
from app.api.errors import registrar_manejadores
from app.api.routers import (
    alertas,
    auth,
    catalogos,
    contratos,
    importacion,
    licitaciones,
    metricas,
)
from app.config import settings
from app.web import routes as web_routes

_CLAVE_EJEMPLO = "dev-inseguro-cambiar-en-produccion"


def create_app() -> FastAPI:
    if settings.auth_required and settings.secret_key == _CLAVE_EJEMPLO:
        raise RuntimeError(
            "AUTH_REQUIRED=true exige una SECRET_KEY real (no la de ejemplo)."
        )
    app = FastAPI(
        title="Sistema de Contratos y Licitaciones",
        version="0.5.0",
        description="API REST + importador + panel web + alertas + reportes + métricas.",
    )
    # Detrás de Firebase Hosting / Cloud Run el esquema e IP reales llegan
    # en X-Forwarded-*; sin esto la app creería que todo es http interno.
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
    registrar_manejadores(app)

    estaticos = Path(__file__).resolve().parent.parent / "web" / "static"
    app.mount("/static", StaticFiles(directory=estaticos), name="static")

    # Sin guardia: login (el propio mecanismo de auth) y /health para monitoreo.
    app.include_router(auth.router)

    # Todo lo demás queda protegido cuando settings.auth_required está activo
    # (el primer usuario se crea con scripts/crear_admin.py, sin pasar por la API).
    protegido = [Depends(guardia)]
    app.include_router(catalogos.router, dependencies=protegido)
    app.include_router(alertas.router, dependencies=protegido)
    app.include_router(metricas.router, dependencies=protegido)
    app.include_router(contratos.router, dependencies=protegido)
    app.include_router(licitaciones.router, dependencies=protegido)
    app.include_router(importacion.router, dependencies=protegido)

    app.include_router(web_routes.router)

    @app.get("/health", tags=["salud"])
    def health() -> dict:
        return {"status": "ok", "etapa": 7}

    return app
