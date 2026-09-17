"""Traduce los errores del dominio a respuestas HTTP."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.state_machine.errors import (
    PrecondicionNoCumplida,
    RolNoAutorizado,
    TransicionNoPermitida,
)


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(RolNoAutorizado)
    async def _rol(request: Request, exc: RolNoAutorizado):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(TransicionNoPermitida)
    async def _transicion(request: Request, exc: TransicionNoPermitida):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(PrecondicionNoCumplida)
    async def _precondicion(request: Request, exc: PrecondicionNoCumplida):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
