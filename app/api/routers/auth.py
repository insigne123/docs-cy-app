"""Autenticación: login y perfil."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, usuario_actual
from app.models.core import Usuario
from app.services.auth import (
    crear_token,
    esta_bloqueado,
    registrar_intento_exitoso,
    registrar_intento_fallido,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    usuario = db.scalars(select(Usuario).where(Usuario.email == email)).first()
    if usuario is not None and (minutos := esta_bloqueado(usuario)) is not None:
        raise HTTPException(status_code=429, detail=f"Demasiados intentos fallidos. Intenta en {minutos} minuto(s).")
    if usuario is None or not verify_password(payload.password, usuario.password_hash):
        if usuario is not None:
            registrar_intento_fallido(usuario)
            db.commit()
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    registrar_intento_exitoso(usuario)
    db.commit()
    return {
        "token": crear_token(usuario.id),
        "usuario": {"id": usuario.id, "nombre": usuario.nombre, "rol": usuario.rol.value},
    }


@router.get("/yo")
def yo(usuario: Usuario | None = Depends(usuario_actual)):
    if usuario is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol.value,
    }
