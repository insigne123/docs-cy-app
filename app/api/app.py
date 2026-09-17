"""Construcción de la aplicación FastAPI."""
from __future__ import annotations

from fastapi import Depends, FastAPI

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
from app.web import routes as web_routes


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sistema de Contratos y Licitaciones",
        version="0.5.0",
        description="API REST + importador + panel web + alertas + reportes + métricas.",
    )
    registrar_manejadores(app)

    # Lectura / auth: sin guardia.
    app.include_router(auth.router)
    app.include_router(catalogos.router)
    app.include_router(alertas.router)
    app.include_router(metricas.router)

    # Escritura de expedientes: protegida cuando settings.auth_required está activo.
    protegido = [Depends(guardia)]
    app.include_router(contratos.router, dependencies=protegido)
    app.include_router(licitaciones.router, dependencies=protegido)
    app.include_router(importacion.router, dependencies=protegido)

    app.include_router(web_routes.router)

    @app.get("/health", tags=["salud"])
    def health() -> dict:
        return {"status": "ok", "etapa": 7}

    return app
