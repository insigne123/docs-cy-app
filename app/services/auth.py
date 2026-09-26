"""Autenticación mínima: hash de contraseñas (PBKDF2) y tokens firmados (HMAC).

Sin dependencias externas. El control de acceso se activa con `settings.auth_required`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings

_ALGO = "pbkdf2_sha256"
_ROUNDS = 200_000

MAX_INTENTOS_LOGIN = 5
BLOQUEO_LOGIN_MINUTOS = 15


def validar_password(password: str) -> Optional[str]:
    """Política mínima de contraseñas. None si es válida, o el mensaje de
    error a mostrar si no lo es."""
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres"
    return None


def hash_password(password: str, *, salt: Optional[bytes] = None, rounds: int = _ROUNDS) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"{_ALGO}${rounds}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, almacenado: Optional[str]) -> bool:
    if not almacenado:
        return False
    try:
        algo, rounds, salt_b64, dk_b64 = almacenado.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt_b64), int(rounds)
        )
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except (ValueError, TypeError):
        return False


def esta_bloqueado(usuario) -> Optional[int]:
    """Minutos que faltan para que el bloqueo termine, o None si no está
    bloqueado. Protege contra fuerza bruta sobre el password de un usuario
    puntual — no sustituye un límite por IP, que necesitaría un almacén
    compartido entre instancias de Cloud Run."""
    if usuario.bloqueado_hasta is None:
        return None
    restante = usuario.bloqueado_hasta - datetime.utcnow()
    if restante.total_seconds() <= 0:
        return None
    return max(1, int(restante.total_seconds() // 60) + 1)


def registrar_intento_fallido(usuario) -> None:
    usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
    if usuario.intentos_fallidos >= MAX_INTENTOS_LOGIN:
        usuario.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=BLOQUEO_LOGIN_MINUTOS)


def registrar_intento_exitoso(usuario) -> None:
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None


def crear_token(usuario_id: int, *, ttl_segundos: int = 8 * 3600) -> str:
    payload = {"uid": int(usuario_id), "exp": int(time.time()) + ttl_segundos}
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    firma = hmac.new(settings.secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{firma}"


def leer_token(token: str) -> Optional[int]:
    try:
        raw, firma = token.split(".", 1)
        esperado = hmac.new(settings.secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(firma, esperado):
            return None
        relleno = "=" * (-len(raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(raw + relleno))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return int(payload["uid"])
    except (ValueError, TypeError, KeyError):
        return None
