"""Expediente contractual y sus entidades hijas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import (
    CategoriaContrato,
    DocumentoTipo,
    EstadoContrato,
    GarantiaEstado,
    GarantiaInstrumento,
    GarantiaTipo,
    HitoEstado,
    HitoTipo,
    LineaContrato,
    Moneda,
    MultaEstado,
    TipoRenovacion,
)
from app.models.base import Base, TimestampMixin, enum_col


class Contrato(Base, TimestampMixin):
    __tablename__ = "contrato"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identificación
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    codigo_externo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    linea: Mapped[LineaContrato] = mapped_column(enum_col(LineaContrato))
    objeto: Mapped[str] = mapped_column(Text)
    categoria: Mapped[Optional[CategoriaContrato]] = mapped_column(
        enum_col(CategoriaContrato), nullable=True
    )

    # Relaciones
    unidad_solicitante_id: Mapped[int] = mapped_column(ForeignKey("unidad.id"))
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    contraparte_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contraparte.id"), nullable=True)
    abogado_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    administrador_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    formato_id: Mapped[Optional[int]] = mapped_column(ForeignKey("formato_estandar.id"), nullable=True)
    # FK lógica a licitacion.id (evita FK circular con licitacion.contrato_id).
    licitacion_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Estado / flujo
    estado: Mapped[EstadoContrato] = mapped_column(enum_col(EstadoContrato))
    estado_desde: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    retorno_a: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    requiere_aprobacion_gerencia: Mapped[bool] = mapped_column(Boolean, default=False)
    requiere_garantia: Mapped[bool] = mapped_column(Boolean, default=False)
    requiere_visacion_contraparte: Mapped[bool] = mapped_column(Boolean, default=False)

    # Montos
    monto: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[Optional[Moneda]] = mapped_column(enum_col(Moneda), nullable=True)
    monto_referencia_clp: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)

    # Fechas del ciclo
    fecha_ingreso: Mapped[date] = mapped_column(Date)
    fecha_aprobacion_jefatura: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_admisibilidad: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_visacion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_firma: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_integracion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Vigencia
    fecha_inicio_vigencia: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_fin_vigencia: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    vigencia_indefinida: Mapped[bool] = mapped_column(Boolean, default=False)
    tipo_renovacion: Mapped[TipoRenovacion] = mapped_column(
        enum_col(TipoRenovacion), default=TipoRenovacion.sin_renovacion
    )
    aviso_previo_dias: Mapped[int] = mapped_column(Integer, default=60)
    causales_termino: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cierre
    motivo_descarte: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha_cierre: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    multas: Mapped[list["Multa"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )
    hitos: Mapped[list["Hito"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )


class Multa(Base, TimestampMixin):
    __tablename__ = "multa"

    id: Mapped[int] = mapped_column(primary_key=True)
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contrato.id"))
    descripcion: Mapped[str] = mapped_column(Text)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    moneda: Mapped[Moneda] = mapped_column(enum_col(Moneda))
    fecha_aplicacion: Mapped[date] = mapped_column(Date)
    estado: Mapped[MultaEstado] = mapped_column(enum_col(MultaEstado), default=MultaEstado.propuesta)
    documento_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    contrato: Mapped["Contrato"] = relationship(back_populates="multas")


class Hito(Base, TimestampMixin):
    __tablename__ = "hito"

    id: Mapped[int] = mapped_column(primary_key=True)
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contrato.id"))
    tipo: Mapped[HitoTipo] = mapped_column(enum_col(HitoTipo))
    nombre: Mapped[str] = mapped_column(String(200))
    fecha_planificada: Mapped[date] = mapped_column(Date)
    fecha_real: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estado: Mapped[HitoEstado] = mapped_column(enum_col(HitoEstado), default=HitoEstado.pendiente)
    responsable_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    contrato: Mapped["Contrato"] = relationship(back_populates="hitos")


class Garantia(Base, TimestampMixin):
    __tablename__ = "garantia"
    __table_args__ = (Index("ix_garantia_entidad", "entidad_tipo", "entidad_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entidad_tipo: Mapped[str] = mapped_column(String(20))  # "contrato" | "licitacion"
    entidad_id: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[GarantiaTipo] = mapped_column(enum_col(GarantiaTipo))
    instrumento: Mapped[GarantiaInstrumento] = mapped_column(enum_col(GarantiaInstrumento))
    emisor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    numero: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    moneda: Mapped[Moneda] = mapped_column(enum_col(Moneda))
    fecha_emision: Mapped[date] = mapped_column(Date)
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    estado: Mapped[GarantiaEstado] = mapped_column(
        enum_col(GarantiaEstado), default=GarantiaEstado.vigente
    )
    glosa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    documento_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Documento(Base, TimestampMixin):
    __tablename__ = "documento"
    __table_args__ = (Index("ix_documento_entidad", "entidad_tipo", "entidad_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entidad_tipo: Mapped[str] = mapped_column(String(20))  # "contrato" | "licitacion"
    entidad_id: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[DocumentoTipo] = mapped_column(enum_col(DocumentoTipo))
    nombre_archivo: Mapped[str] = mapped_column(String(255))
    ruta: Mapped[str] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, default=1)
    hash_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cargado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    cargado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Contenido real del archivo subido, para poder previsualizarlo (antes
    # 'ruta' era solo texto libre, sin un archivo real detrás). Nulo en
    # documentos registrados antes de esta funcionalidad.
    content_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    contenido: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)


class Comentario(Base, TimestampMixin):
    """Nota libre en la ficha de un contrato o licitación — bitácora aparte
    de los cambios de estado (EventoEstado), para dejar contexto que no
    encaja en un comentario de transición."""
    __tablename__ = "comentario"
    __table_args__ = (Index("ix_comentario_entidad", "entidad_tipo", "entidad_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entidad_tipo: Mapped[str] = mapped_column(String(20))  # "contrato" | "licitacion"
    entidad_id: Mapped[int] = mapped_column(Integer)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    texto: Mapped[str] = mapped_column(Text)
