"""Dependencias de FastAPI."""
from __future__ import annotations

import logging

from typing import Iterator, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.enums import Rol
from app.models.core import Usuario
from app.services.auth import leer_token

log = logging.getLogger(__name__)

# Nombre de la cookie de sesión. Firebase Hosting solo reenvía a Cloud Run
# las cookies llamadas `__session`; cualquier otro nombre se pierde en el proxy.
COOKIE_SESION = "__session"


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
    token = token or request.cookies.get(COOKIE_SESION)
    if not token:
        return None
    uid = leer_token(token)
    if uid is None:
        log.warning("token de sesión inválido o expirado")
        return None
    return db.get(Usuario, uid) if uid else None


def guardia(usuario: Optional[Usuario] = Depends(usuario_actual)) -> Optional[Usuario]:
    """Dependencia de router: exige autenticación sólo si `settings.auth_required`."""
    if settings.auth_required and usuario is None:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    return usuario


def exigir_admin_sistema(usuario: Optional[Usuario] = Depends(usuario_actual)) -> Optional[Usuario]:
    """Para endpoints de catálogos (unidades, usuarios, contrapartes, formatos,
    parámetros) que en el panel web ya son exclusivos de admin_sistema — sin
    esto, cualquier usuario autenticado podía llamar la API directamente y
    saltarse esa restricción (p. ej. crearse a sí mismo una cuenta admin).
    Sin `settings.auth_required` (uso interno/pruebas) no se restringe nada,
    igual que el resto de la API."""
    if not settings.auth_required:
        return usuario
    if usuario is None or usuario.rol.value != "admin_sistema":
        raise HTTPException(status_code=403, detail="Se requiere el rol admin_sistema")
    return usuario


def exigir_roles(*roles: Rol):
    """Fábrica de dependencia para los sub-recursos de contrato/licitación que
    en el panel web ya están limitados a roles concretos (garantías, hitos,
    multas) pero cuyo endpoint de API no pasa por el motor de estados —
    resolver_actor_transicion() no los cubre porque no son transiciones.
    admin_sistema siempre puede, igual que en el panel (_requiere_rol)."""
    nombres_permitidos = {r.value for r in roles}

    def _dep(usuario: Optional[Usuario] = Depends(usuario_actual)) -> Optional[Usuario]:
        if not settings.auth_required:
            return usuario
        if usuario is None:
            raise HTTPException(status_code=401, detail="Autenticación requerida")
        if usuario.rol.value not in nombres_permitidos and usuario.rol.value != "admin_sistema":
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere uno de estos roles: {', '.join(sorted(nombres_permitidos))}",
            )
        return usuario

    return _dep


def resolver_actor_transicion(
    db: Session,
    payload_usuario_id: int,
    payload_rol,
    sesion_usuario: Optional[Usuario],
):
    """Determina qué usuario y rol usa el motor de estados para autorizar una
    transición. Con auth obligatoria, la identidad SIEMPRE viene de la sesión
    autenticada, nunca del cuerpo de la solicitud: de lo contrario cualquier
    llamada autenticada podía indicar un usuario_id/rol arbitrario en el JSON
    y suplantar a otra persona (p. ej. actuar como admin_sistema sin serlo).
    Sin auth obligatoria (uso interno/pruebas) se mantiene el comportamiento
    histórico de confiar en el payload."""
    if settings.auth_required:
        if sesion_usuario is None:
            raise HTTPException(status_code=401, detail="Autenticación requerida")
        return sesion_usuario, None
    usuario = obtener_o_404(db, Usuario, payload_usuario_id, "Usuario")
    return usuario, payload_rol
