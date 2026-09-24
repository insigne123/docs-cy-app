"""Definición declarativa de las transiciones de contrato y de licitación.

Ver docs/02-maquina-de-estados.md para la especificación de negocio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from app.enums import EstadoContrato as E
from app.enums import EstadoLicitacion as LE
from app.enums import LineaContrato as L
from app.enums import Rol as R
import app.state_machine.guards as g
from app.state_machine.context import ContextoTransicion

Guard = Callable[[ContextoTransicion], None]


@dataclass(frozen=True)
class Transicion:
    codigo: str
    desde: str
    hacia: str
    roles: frozenset[str]
    lineas: frozenset[str] = frozenset()      # vacío = no aplica filtro de línea
    guard: Optional[Guard] = None
    efecto: Optional[Guard] = None
    set_retorno_a: Optional[str] = None       # valor a guardar al ENTRAR a 'aclaraciones'


def _r(*roles: R) -> frozenset[str]:
    return frozenset(x.value for x in roles)


_A = frozenset({L.A_regular.value})
_B = frozenset({L.B_autogestionado.value})
_C = frozenset({L.C_licitacion.value})
_AB = _A | _B
_ABC = _A | _B | _C


# ============================================================ CONTRATO
TRANSICIONES_CONTRATO: list[Transicion] = [
    # ---------- Línea A: Flujo Regular / Abastecimiento
    Transicion("A2", E.ingreso.value, E.aprobacion_jefatura.value,
               _r(R.unidad_solicitante, R.admin_sistema), _A, guard=g.g_completitud_ok),
    Transicion("A3", E.ingreso.value, E.aclaraciones.value,
               _r(R.unidad_solicitante, R.admin_sistema, R.legal), _A,
               guard=g.g_completitud_falla, set_retorno_a=E.ingreso.value),
    Transicion("A4", E.aprobacion_jefatura.value, E.aprobacion_gerencia.value,
               _r(R.jefatura), _A, guard=g.g_requiere_gerencia, efecto=g.ef_fecha_aprobacion_jefatura),
    Transicion("A5", E.aprobacion_jefatura.value, E.admisibilidad_1.value,
               _r(R.jefatura), _A, guard=g.g_no_requiere_gerencia, efecto=g.ef_fecha_aprobacion_jefatura),
    Transicion("A6", E.aprobacion_gerencia.value, E.admisibilidad_1.value,
               _r(R.gerencia), _A),
    Transicion("A7", E.admisibilidad_1.value, E.admisibilidad_2.value,
               _r(R.legal), _A),
    Transicion("A8", E.admisibilidad_1.value, E.aclaraciones.value,
               _r(R.legal), _A, set_retorno_a=E.admisibilidad_1.value),
    Transicion("A9", E.admisibilidad_2.value, E.elaboracion.value,
               _r(R.legal), _A, guard=g.g_abogado_asignado, efecto=g.ef_fecha_admisibilidad),
    Transicion("A10", E.elaboracion.value, E.visacion.value,
               _r(R.legal), _A, guard=g.g_borrador_cargado),
    Transicion("A11", E.elaboracion.value, E.aclaraciones.value,
               _r(R.legal), _A, set_retorno_a=E.elaboracion.value),
    Transicion("A12", E.visacion.value, E.firma.value,
               _r(R.legal, R.unidad_solicitante), _A,
               guard=g.combinar(g.g_visacion_ok, g.g_garantia_si_requiere), efecto=g.ef_fecha_visacion),
    Transicion("A13", E.visacion.value, E.elaboracion.value,
               _r(R.legal), _A),
    Transicion("A14", E.firma.value, E.integracion.value,
               _r(R.legal), _A, guard=g.g_documento_firmado, efecto=g.ef_fecha_firma),

    # ---------- Línea B: Flujo Express / Autogestionado
    Transicion("B2", E.ingreso.value, E.admisibilidad_1.value,
               _r(R.unidad_solicitante, R.admin_sistema), _B,
               guard=g.combinar(g.g_completitud_ok, g.g_no_requiere_gerencia)),
    Transicion("B2g", E.ingreso.value, E.aprobacion_gerencia.value,
               _r(R.unidad_solicitante, R.admin_sistema), _B,
               guard=g.combinar(g.g_completitud_ok, g.g_requiere_gerencia)),
    Transicion("B2h", E.aprobacion_gerencia.value, E.admisibilidad_1.value,
               _r(R.gerencia), _B),
    Transicion("B3", E.ingreso.value, E.aclaraciones.value,
               _r(R.unidad_solicitante, R.admin_sistema, R.legal), _B,
               guard=g.g_completitud_falla, set_retorno_a=E.ingreso.value),
    Transicion("B4", E.admisibilidad_1.value, E.visacion.value,
               _r(R.legal), _B, guard=g.g_formato_no_modificado, efecto=g.ef_fecha_admisibilidad),
    Transicion("B5", E.admisibilidad_1.value, E.aclaraciones.value,
               _r(R.legal), _B, set_retorno_a=E.admisibilidad_1.value),
    Transicion("B7", E.visacion.value, E.firma.value,
               _r(R.legal, R.unidad_solicitante), _B,
               guard=g.combinar(g.g_visacion_ok, g.g_garantia_si_requiere), efecto=g.ef_fecha_visacion),
    Transicion("B8", E.firma.value, E.integracion.value,
               _r(R.legal), _B, guard=g.g_documento_firmado, efecto=g.ef_fecha_firma),

    # ---------- Línea C: Fase II (Formalización)
    Transicion("C14", E.formalizacion_ajuste.value, E.constitucion_garantias.value,
               _r(R.legal), _C, guard=g.g_coherente_con_oferta),
    Transicion("C15", E.constitucion_garantias.value, E.firma.value,
               _r(R.financiera), _C, guard=g.g_garantia_cumplimiento_vigente),
    Transicion("C16", E.firma.value, E.integracion.value,
               _r(R.legal), _C, guard=g.g_documento_firmado, efecto=g.ef_fecha_firma),

    # ---------- Compartidas (todas las líneas)
    Transicion("INT_VIG", E.integracion.value, E.vigente.value,
               _r(R.admin_contratos), _ABC,
               guard=g.g_puede_pasar_a_vigente, efecto=g.combinar(g.ef_fecha_integracion, g.ef_iniciar_vigencia)),
    Transicion("RENOV", E.vigente.value, E.vigente.value,
               _r(R.admin_contratos), _ABC, efecto=g.ef_renovacion),
    Transicion("TERM", E.vigente.value, E.terminado.value,
               _r(R.admin_contratos), _ABC, efecto=g.ef_terminar),

    # ---------- Salida de 'aclaraciones' (el motor valida que hacia == contrato.retorno_a)
    Transicion("ACL_ingreso", E.aclaraciones.value, E.ingreso.value,
               _r(R.unidad_solicitante), _AB),
    Transicion("ACL_adm1", E.aclaraciones.value, E.admisibilidad_1.value,
               _r(R.unidad_solicitante), _AB),
    Transicion("ACL_elab", E.aclaraciones.value, E.elaboracion.value,
               _r(R.unidad_solicitante), _A),
]


# ============================================================ LICITACIÓN
_ROLES_EXAMEN = _r(R.tecnica, R.financiera, R.legal, R.gerencia)

TRANSICIONES_LICITACION: list[Transicion] = [
    Transicion("L1", LE.ingreso_antecedentes.value, LE.examen_admisibilidad.value,
               _r(R.admin_licitaciones)),
    Transicion("L2", LE.examen_admisibilidad.value, LE.revision_bases.value,
               _ROLES_EXAMEN),
    Transicion("L3", LE.revision_bases.value, LE.preparacion_oferta.value,
               _r(R.legal, R.tecnica), guard=g.g_informe_riesgos),
    Transicion("L4", LE.preparacion_oferta.value, LE.presentacion_oferta.value,
               _r(R.tecnica, R.financiera, R.legal), guard=g.g_oferta_lista),
    Transicion("L5", LE.presentacion_oferta.value, LE.evaluacion_resultado.value,
               _r(R.admin_licitaciones)),
    Transicion("L6", LE.evaluacion_resultado.value, LE.adjudicada.value,
               _r(R.admin_licitaciones, R.gerencia), efecto=g.ef_adjudicada),
    Transicion("L7", LE.evaluacion_resultado.value, LE.no_adjudicada.value,
               _r(R.admin_licitaciones), guard=g.g_analisis_interno, efecto=g.ef_no_adjudicada),
    Transicion("L8", LE.evaluacion_resultado.value, LE.desierta.value,
               _r(R.admin_licitaciones), efecto=g.ef_desierta),
    Transicion("L9", LE.evaluacion_resultado.value, LE.desistida.value,
               _r(R.admin_licitaciones), efecto=g.ef_desistida),
]


def buscar(
    transiciones: list[Transicion], desde: str, hacia: str, linea_val: Optional[str]
) -> Optional[Transicion]:
    for t in transiciones:
        if t.desde != desde or t.hacia != hacia:
            continue
        if t.lineas and (linea_val is None or linea_val not in t.lineas):
            continue
        return t
    return None


def transiciones_disponibles(desde: str, linea_val: Optional[str]) -> list[str]:
    """Estados destino alcanzables desde `desde` para esa línea (para armar el formulario
    de avance del panel web). No incluye 'descartado' (siempre disponible aparte) ni
    resuelve el caso especial de 'aclaraciones' (ver `app/web/routes.py`)."""
    vistos: list[str] = []
    for t in TRANSICIONES_CONTRATO:
        if t.desde != desde:
            continue
        if t.lineas and (linea_val is None or linea_val not in t.lineas):
            continue
        if t.hacia not in vistos:
            vistos.append(t.hacia)
    return vistos
