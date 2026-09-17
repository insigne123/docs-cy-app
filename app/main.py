"""Punto de entrada ASGI.

Ejecutar en local:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

from app.api.app import create_app

app = create_app()
