"""Modelos base de organización y catálogos."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import ContraparteTipo, Rol, UnidadTipo
from app.models.base import Base, TimestampMixin, enum_col


class Unidad(Base, TimestampMixin):
    __tablename__ = "unidad"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    tipo: Mapped[UnidadTipo] = mapped_column(enum_col(UnidadTipo))
    # FK lógica a usuario.id (evita FK circular Usuario<->Unidad); sin ORM relationship.
    jefatura_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    rol: Mapped[Rol] = mapped_column(enum_col(Rol))
    unidad_id: Mapped[Optional[int]] = mapped_column(ForeignKey("unidad.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Contraparte(Base, TimestampMixin):
    __tablename__ = "contraparte"

    id: Mapped[int] = mapped_column(primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200))
    rut: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    tipo: Mapped[ContraparteTipo] = mapped_column(enum_col(ContraparteTipo))
    contacto_nombre: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    contacto_email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    contacto_telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Parametro(Base, TimestampMixin):
    __tablename__ = "parametro"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(String(255))
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class FormatoEstandar(Base, TimestampMixin):
    __tablename__ = "formato_estandar"
    __table_args__ = (UniqueConstraint("nombre", "version", name="uq_formato_nombre_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    version: Mapped[int] = mapped_column(Integer, default=1)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)
    aprobado_por: Mapped[str] = mapped_column(String(120))
    fecha_aprobacion: Mapped[date] = mapped_column(Date)
    campos_variables: Mapped[list] = mapped_column(JSON, default=list)
    ruta_plantilla: Mapped[str] = mapped_column(String(255))
    checksum_base: Mapped[str] = mapped_column(String(128))
    # Contenido real del archivo subido, para poder previsualizarlo desde el
    # panel (antes solo se guardaba el checksum). Nulo en formatos creados
    # antes de esta funcionalidad.
    nombre_archivo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    contenido: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
