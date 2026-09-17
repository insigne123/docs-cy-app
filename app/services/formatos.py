"""Verificación del clausulado estándar (Línea B): comparación de checksum SHA-256."""
from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.models.core import FormatoEstandar


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verificar_formato(session: Session, formato_id: int, data: bytes) -> dict:
    formato = session.get(FormatoEstandar, formato_id)
    if formato is None:
        raise ValueError(f"Formato {formato_id} no encontrado")
    recibido = sha256_bytes(data)
    return {
        "formato": formato.nombre,
        "version": formato.version,
        "checksum_esperado": formato.checksum_base,
        "checksum_recibido": recibido,
        "coincide": recibido == formato.checksum_base,
    }
