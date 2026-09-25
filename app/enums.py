"""Enumeraciones del dominio. Ver docs/01-diccionario-de-datos.md y docs/02-maquina-de-estados.md.

Todas heredan de (str, Enum): el valor de cada miembro coincide con su nombre, de modo que
se pueden comparar indistintamente con strings y persistir como texto.
"""
from __future__ import annotations

import enum


class _StrEnum(str, enum.Enum):
    def __str__(self) -> str:  # pragma: no cover - conveniencia
        return self.value


class Rol(_StrEnum):
    unidad_solicitante = "unidad_solicitante"
    jefatura = "jefatura"
    legal = "legal"
    admin_licitaciones = "admin_licitaciones"
    financiera = "financiera"
    tecnica = "tecnica"
    gerencia = "gerencia"
    admin_contratos = "admin_contratos"
    admin_sistema = "admin_sistema"


# Icono por rol para las tablas de usuarios y la línea de tiempo (ver base.html /
# catalogos.html / detalle.html): un identificador visual rápido, no persistido.
ICONOS_ROL: dict[str, str] = {
    Rol.unidad_solicitante.value: "🗂️",
    Rol.jefatura.value: "🧭",
    Rol.legal.value: "⚖️",
    Rol.admin_licitaciones.value: "📋",
    Rol.financiera.value: "💰",
    Rol.tecnica.value: "🛠️",
    Rol.gerencia.value: "🏛️",
    Rol.admin_contratos.value: "📁",
    Rol.admin_sistema.value: "🛡️",
}


def icono_rol(valor: str) -> str:
    return ICONOS_ROL.get(valor, "👤")


class Moneda(_StrEnum):
    CLP = "CLP"
    UF = "UF"
    USD = "USD"
    EUR = "EUR"
    otro = "otro"


class UnidadTipo(_StrEnum):
    solicitante = "solicitante"
    interna = "interna"


class ContraparteTipo(_StrEnum):
    proveedor = "proveedor"
    cliente = "cliente"
    mandante = "mandante"
    otro = "otro"


class LineaContrato(_StrEnum):
    A_regular = "A_regular"
    B_autogestionado = "B_autogestionado"
    C_licitacion = "C_licitacion"


# Nombres para mostrar en el panel y los reportes (el valor interno del enum no cambia:
# ya está persistido en la base de datos de producción).
NOMBRES_LINEA: dict[str, str] = {
    LineaContrato.A_regular.value: "Flujo Regular",
    LineaContrato.B_autogestionado.value: "Flujo Autogestionado",
    LineaContrato.C_licitacion.value: "Licitaciones",
}


def nombre_linea(valor: str) -> str:
    return NOMBRES_LINEA.get(valor, valor)


class CategoriaContrato(_StrEnum):
    servicio = "servicio"
    suministro = "suministro"
    arriendo = "arriendo"
    obra = "obra"
    licencia = "licencia"
    otro = "otro"


class TipoRenovacion(_StrEnum):
    sin_renovacion = "sin_renovacion"
    automatica = "automatica"
    con_aviso = "con_aviso"
    manual = "manual"


class EstadoContrato(_StrEnum):
    ingreso = "ingreso"
    aprobacion_jefatura = "aprobacion_jefatura"
    aprobacion_gerencia = "aprobacion_gerencia"
    admisibilidad_1 = "admisibilidad_1"
    admisibilidad_2 = "admisibilidad_2"
    elaboracion = "elaboracion"
    visacion = "visacion"
    firma = "firma"
    integracion = "integracion"
    vigente = "vigente"
    terminado = "terminado"
    aclaraciones = "aclaraciones"
    descartado = "descartado"
    # Línea C — Fase II (Formalización)
    formalizacion_ajuste = "formalizacion_ajuste"
    constitucion_garantias = "constitucion_garantias"


class EstadoLicitacion(_StrEnum):
    ingreso_antecedentes = "ingreso_antecedentes"
    examen_admisibilidad = "examen_admisibilidad"
    revision_bases = "revision_bases"
    preparacion_oferta = "preparacion_oferta"
    presentacion_oferta = "presentacion_oferta"
    evaluacion_resultado = "evaluacion_resultado"
    adjudicada = "adjudicada"
    no_adjudicada = "no_adjudicada"
    desierta = "desierta"
    desistida = "desistida"
    descartado = "descartado"


class LicitacionFase(_StrEnum):
    pre_adjudicacion = "pre_adjudicacion"
    formalizacion = "formalizacion"
    cerrada = "cerrada"


class LicitacionResultado(_StrEnum):
    en_proceso = "en_proceso"
    adjudicado = "adjudicado"
    no_adjudicado = "no_adjudicado"
    desierto = "desierto"
    desistido = "desistido"


class GarantiaTipo(_StrEnum):
    seriedad_oferta = "seriedad_oferta"
    fiel_cumplimiento = "fiel_cumplimiento"
    anticipo = "anticipo"
    correcta_ejecucion = "correcta_ejecucion"
    otra = "otra"


class GarantiaInstrumento(_StrEnum):
    boleta_bancaria = "boleta_bancaria"
    poliza_seguro = "poliza_seguro"
    retencion = "retencion"
    pagare = "pagare"
    otro = "otro"


class GarantiaEstado(_StrEnum):
    vigente = "vigente"
    por_vencer = "por_vencer"
    vencida = "vencida"
    ejecutada = "ejecutada"
    devuelta = "devuelta"
    reemplazada = "reemplazada"


class MultaEstado(_StrEnum):
    propuesta = "propuesta"
    aplicada = "aplicada"
    en_disputa = "en_disputa"
    pagada = "pagada"
    condonada = "condonada"


class HitoTipo(_StrEnum):
    inicio_ejecucion = "inicio_ejecucion"
    entregable = "entregable"
    pago = "pago"
    renovacion = "renovacion"
    termino = "termino"
    revision = "revision"
    otro = "otro"


class HitoEstado(_StrEnum):
    pendiente = "pendiente"
    cumplido = "cumplido"
    atrasado = "atrasado"
    cancelado = "cancelado"


class DocumentoTipo(_StrEnum):
    solicitud = "solicitud"
    antecedente = "antecedente"
    borrador = "borrador"
    contrato_firmado = "contrato_firmado"
    anexo = "anexo"
    garantia = "garantia"
    bases = "bases"
    oferta_tecnica = "oferta_tecnica"
    oferta_economica = "oferta_economica"
    informe_riesgos = "informe_riesgos"
    acta = "acta"
    otro = "otro"


class EntidadTipo(_StrEnum):
    contrato = "contrato"
    licitacion = "licitacion"


ESTADOS_CONTRATO_TERMINALES = frozenset({EstadoContrato.terminado, EstadoContrato.descartado})
ESTADOS_LICITACION_TERMINALES = frozenset(
    {
        EstadoLicitacion.no_adjudicada,
        EstadoLicitacion.desierta,
        EstadoLicitacion.desistida,
        EstadoLicitacion.descartado,
    }
)
