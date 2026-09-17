"""Registra todos los modelos en la metadata de SQLAlchemy."""
from app.models.base import Base
from app.models.core import Contraparte, FormatoEstandar, Parametro, Unidad, Usuario
from app.models.contrato import Contrato, Documento, Garantia, Hito, Multa
from app.models.evento import EventoEstado
from app.models.licitacion import Licitacion

__all__ = [
    "Base",
    "Unidad",
    "Usuario",
    "Contraparte",
    "Parametro",
    "FormatoEstandar",
    "Contrato",
    "Multa",
    "Hito",
    "Garantia",
    "Documento",
    "Licitacion",
    "EventoEstado",
]
