"""Contexto que se pasa a guards y efectos de cada transición."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session


@dataclass
class ContextoTransicion:
    session: Session
    entidad: Any                 # Contrato o Licitacion
    entidad_tipo: str            # "contrato" | "licitacion"
    usuario: Any                 # Usuario
    rol: str                     # valor de Rol con el que actúa
    hacia: str                   # estado destino (valor)
    fecha: datetime
    comentario: str | None = None
    retorno_a: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
