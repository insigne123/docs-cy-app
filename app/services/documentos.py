"""Subida y consulta del archivo real detrás de un Documento (borrador,
contrato firmado, bases, oferta técnica, etc.). Antes 'ruta' era solo texto
libre y no había ningún archivo real guardado — igual que pasaba con los
Formatos estándar antes de agregarles previsualización."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import DocumentoTipo
from app.models.contrato import Documento
from app.services.formatos import sha256_bytes


def subir_documento(
    session: Session,
    *,
    entidad_tipo: str,
    entidad_id: int,
    tipo: DocumentoTipo,
    nombre_archivo: str,
    content_type: str,
    contenido: bytes,
    cargado_por_id: int,
) -> Documento:
    version_anterior = session.scalar(
        select(func.max(Documento.version)).where(
            Documento.entidad_tipo == entidad_tipo,
            Documento.entidad_id == entidad_id,
            Documento.tipo == tipo,
        )
    )
    documento = Documento(
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        tipo=tipo,
        nombre_archivo=nombre_archivo,
        ruta=f"{entidad_tipo}/{entidad_id}/{nombre_archivo}",
        version=(version_anterior or 0) + 1,
        hash_sha256=sha256_bytes(contenido),
        cargado_por_id=cargado_por_id,
        cargado_en=datetime.utcnow(),
        content_type=content_type,
        contenido=contenido,
    )
    session.add(documento)
    return documento
