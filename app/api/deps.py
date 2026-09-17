"""Dependencias de FastAPI."""
from __future__ import annotations

from typing import Iterator, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.core import Usuario
from app.services.auth import leer_token


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def obtener_o_404(db: Session, modelo, ident, nombre: str):
    obj = db.get(modelo, ident)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{nombre} {ident} no encontrado")
    return obj


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Optional[Usuario]:
    token = None
    cabecera = request.headers.get("Authorization", "")
    if cabecera.startswith("Bearer "):
        token = cabecera[7:]
    token = token or request.cookies.get("token")
    if not token:
        return None
    uid = leer_token(token)
    return db.get(Usuario, uid) if uid else None


def guardia(usuario: Optional[Usuario] = Depends(usuario_actual)) -> Optional[Usuario]:
    """Dependencia de router: exige autenticación sólo si `settings.auth_required`."""
    if settings.auth_required and usuario is None:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    return usuario
