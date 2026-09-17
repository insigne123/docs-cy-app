"""Esquemas Pydantic de entrada y salida de la API."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.enums import (
    CategoriaContrato,
    ContraparteTipo,
    DocumentoTipo,
    EstadoContrato,
    EstadoLicitacion,
    GarantiaEstado,
    GarantiaInstrumento,
    GarantiaTipo,
    HitoEstado,
    HitoTipo,
    LineaContrato,
    Moneda,
    MultaEstado,
    Rol,
    TipoRenovacion,
    UnidadTipo,
)


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------- catálogos
class UnidadIn(BaseModel):
    nombre: str
    tipo: UnidadTipo = UnidadTipo.solicitante
    jefatura_id: Optional[int] = None


class UnidadOut(_ORM):
    id: int
    nombre: str
    tipo: UnidadTipo
    jefatura_id: Optional[int]
    activo: bool


class UsuarioIn(BaseModel):
    nombre: str
    email: str
    rol: Rol
    unidad_id: Optional[int] = None
    password: Optional[str] = None


class UsuarioOut(_ORM):
    id: int
    nombre: str
    email: str
    rol: Rol
    unidad_id: Optional[int]
    activo: bool


class ContraparteIn(BaseModel):
    razon_social: str
    tipo: ContraparteTipo = ContraparteTipo.proveedor
    rut: Optional[str] = None
    contacto_nombre: Optional[str] = None
    contacto_email: Optional[str] = None
    contacto_telefono: Optional[str] = None
    notas: Optional[str] = None


class ContraparteOut(_ORM):
    id: int
    razon_social: str
    tipo: ContraparteTipo
    rut: Optional[str]
    contacto_nombre: Optional[str]
    contacto_email: Optional[str]
    contacto_telefono: Optional[str]


class FormatoIn(BaseModel):
    nombre: str
    version: int = 1
    vigente: bool = True
    aprobado_por: str
    fecha_aprobacion: date
    campos_variables: list[str] = []
    ruta_plantilla: str
    checksum_base: str


class FormatoOut(_ORM):
    id: int
    nombre: str
    version: int
    vigente: bool
    aprobado_por: str
    fecha_aprobacion: date
    campos_variables: list
    ruta_plantilla: str
    checksum_base: str


class ParametroOut(_ORM):
    clave: str
    valor: str
    descripcion: Optional[str]


class ParametroUpdate(BaseModel):
    valor: str


# --------------------------------------------------------------------- contrato
class ContratoIn(BaseModel):
    codigo: str
    linea: LineaContrato
    objeto: str
    unidad_solicitante_id: int
    solicitante_id: int
    contraparte_id: Optional[int] = None
    formato_id: Optional[int] = None
    categoria: Optional[CategoriaContrato] = None
    monto: Optional[Decimal] = None
    moneda: Optional[Moneda] = None
    monto_referencia_clp: Optional[Decimal] = None
    requiere_garantia: bool = False
    requiere_visacion_contraparte: bool = False
    fecha_ingreso: Optional[date] = None


class ContratoUpdate(BaseModel):
    objeto: Optional[str] = None
    categoria: Optional[CategoriaContrato] = None
    contraparte_id: Optional[int] = None
    abogado_id: Optional[int] = None
    administrador_id: Optional[int] = None
    monto: Optional[Decimal] = None
    moneda: Optional[Moneda] = None
    monto_referencia_clp: Optional[Decimal] = None
    requiere_garantia: Optional[bool] = None
    requiere_visacion_contraparte: Optional[bool] = None
    fecha_inicio_vigencia: Optional[date] = None
    fecha_fin_vigencia: Optional[date] = None
    vigencia_indefinida: Optional[bool] = None
    tipo_renovacion: Optional[TipoRenovacion] = None
    aviso_previo_dias: Optional[int] = None
    causales_termino: Optional[str] = None


class ContratoOut(_ORM):
    id: int
    codigo: str
    codigo_externo: Optional[str]
    linea: LineaContrato
    objeto: str
    categoria: Optional[CategoriaContrato]
    unidad_solicitante_id: int
    solicitante_id: int
    contraparte_id: Optional[int]
    abogado_id: Optional[int]
    administrador_id: Optional[int]
    formato_id: Optional[int]
    licitacion_id: Optional[int]
    estado: EstadoContrato
    estado_desde: datetime
    retorno_a: Optional[str]
    requiere_aprobacion_gerencia: bool
    requiere_garantia: bool
    requiere_visacion_contraparte: bool
    monto: Optional[Decimal]
    moneda: Optional[Moneda]
    monto_referencia_clp: Optional[Decimal]
    fecha_ingreso: date
    fecha_aprobacion_jefatura: Optional[date]
    fecha_admisibilidad: Optional[date]
    fecha_visacion: Optional[date]
    fecha_firma: Optional[date]
    fecha_integracion: Optional[date]
    fecha_inicio_vigencia: Optional[date]
    fecha_fin_vigencia: Optional[date]
    vigencia_indefinida: bool
    tipo_renovacion: TipoRenovacion
    aviso_previo_dias: int
    causales_termino: Optional[str]
    motivo_descarte: Optional[str]
    fecha_cierre: Optional[date]


# --------------------------------------------------------------------- sub-recursos
class GarantiaIn(BaseModel):
    tipo: GarantiaTipo
    instrumento: GarantiaInstrumento
    monto: Decimal
    moneda: Moneda
    fecha_emision: date
    fecha_vencimiento: date
    emisor: Optional[str] = None
    numero: Optional[str] = None
    estado: GarantiaEstado = GarantiaEstado.vigente
    glosa: Optional[str] = None


class GarantiaOut(_ORM):
    id: int
    entidad_tipo: str
    entidad_id: int
    tipo: GarantiaTipo
    instrumento: GarantiaInstrumento
    emisor: Optional[str]
    numero: Optional[str]
    monto: Decimal
    moneda: Moneda
    fecha_emision: date
    fecha_vencimiento: date
    estado: GarantiaEstado
    glosa: Optional[str]


class HitoIn(BaseModel):
    tipo: HitoTipo
    nombre: str
    fecha_planificada: date
    fecha_real: Optional[date] = None
    estado: HitoEstado = HitoEstado.pendiente
    responsable_id: Optional[int] = None
    notas: Optional[str] = None


class HitoOut(_ORM):
    id: int
    contrato_id: int
    tipo: HitoTipo
    nombre: str
    fecha_planificada: date
    fecha_real: Optional[date]
    estado: HitoEstado
    responsable_id: Optional[int]
    notas: Optional[str]


class MultaIn(BaseModel):
    descripcion: str
    monto: Decimal
    moneda: Moneda
    fecha_aplicacion: date
    estado: MultaEstado = MultaEstado.propuesta


class MultaOut(_ORM):
    id: int
    contrato_id: int
    descripcion: str
    monto: Decimal
    moneda: Moneda
    fecha_aplicacion: date
    estado: MultaEstado


class DocumentoIn(BaseModel):
    tipo: DocumentoTipo
    nombre_archivo: str
    ruta: str
    cargado_por_id: int
    version: int = 1
    hash_sha256: Optional[str] = None


class DocumentoOut(_ORM):
    id: int
    entidad_tipo: str
    entidad_id: int
    tipo: DocumentoTipo
    nombre_archivo: str
    ruta: str
    version: int
    hash_sha256: Optional[str]
    cargado_por_id: int
    cargado_en: datetime


class EventoOut(_ORM):
    id: int
    entidad_tipo: str
    entidad_id: int
    estado_origen: Optional[str]
    estado_destino: str
    fecha: datetime
    usuario_id: int
    rol_actor: str
    comentario: Optional[str]
    retorno_a: Optional[str]


class TransicionIn(BaseModel):
    hacia: str
    usuario_id: int
    rol: Optional[Rol] = None
    comentario: Optional[str] = None
    retorno_a: Optional[str] = None
    extra: dict[str, Any] = {}


class FichaContrato(BaseModel):
    contrato: ContratoOut
    garantias: list[GarantiaOut]
    hitos: list[HitoOut]
    multas: list[MultaOut]
    documentos: list[DocumentoOut]
    historial: list[EventoOut]


# --------------------------------------------------------------------- licitación
class LicitacionIn(BaseModel):
    codigo: str
    objeto: str
    unidad_solicitante_id: int
    solicitante_id: int
    contraparte_id: Optional[int] = None
    mandante: Optional[str] = None
    moneda: Optional[Moneda] = None
    exige_garantia_seriedad: bool = False
    fecha_ingreso: Optional[date] = None


class LicitacionUpdate(BaseModel):
    objeto: Optional[str] = None
    mandante: Optional[str] = None
    contraparte_id: Optional[int] = None
    moneda: Optional[Moneda] = None
    exige_garantia_seriedad: Optional[bool] = None
    fecha_publicacion_bases: Optional[date] = None
    fecha_cierre_ofertas: Optional[date] = None
    fecha_apertura: Optional[date] = None
    presupuesto_referencia: Optional[Decimal] = None
    informe_riesgos_id: Optional[int] = None


class LicitacionOut(_ORM):
    id: int
    codigo: str
    objeto: str
    mandante: Optional[str]
    contraparte_id: Optional[int]
    unidad_solicitante_id: int
    fase: str
    estado: EstadoLicitacion
    fecha_ingreso: date
    fecha_publicacion_bases: Optional[date]
    fecha_cierre_ofertas: Optional[date]
    fecha_apertura: Optional[date]
    presupuesto_referencia: Optional[Decimal]
    moneda: Optional[Moneda]
    exige_garantia_seriedad: bool
    resultado: str
    fecha_resultado: Optional[date]
    contrato_id: Optional[int]
    informe_riesgos_id: Optional[int]
    analisis_interno: Optional[str]


class TransicionLicitacionIn(BaseModel):
    hacia: EstadoLicitacion
    usuario_id: int
    rol: Optional[Rol] = None
    comentario: Optional[str] = None
    extra: dict[str, Any] = {}


class AdjudicarIn(BaseModel):
    usuario_id: int
    codigo_contrato: str
    objeto: Optional[str] = None
    contraparte_id: Optional[int] = None
    comentario: str = "Adjudicación de la licitación"


class FichaLicitacion(BaseModel):
    licitacion: LicitacionOut
    garantias: list[GarantiaOut]
    documentos: list[DocumentoOut]
    historial: list[EventoOut]


# --------------------------------------------------------------------- importación
class ImportarIn(BaseModel):
    archivo: str
    carpeta: Optional[str] = None


class ResultadoImportacionOut(BaseModel):
    creados: list[str]
    actualizados: list[str]
    errores: list[dict]
    advertencias: list[str]
