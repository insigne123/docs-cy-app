"""Precondiciones (guards) y efectos de las transiciones.

Cada guard recibe un ContextoTransicion y lanza PrecondicionNoCumplida si no se cumple.
Los flags de `ctx.extra` permiten simular en pruebas hechos que en producción vendrán de
documentos cargados o validaciones de otras áreas.
"""
from __future__ import annotations

from datetime import date

from app.enums import (
    DocumentoTipo,
    GarantiaTipo,
    HitoEstado,
    HitoTipo,
    LicitacionResultado,
)
from app.models.contrato import Hito
from app.state_machine.context import ContextoTransicion
from app.state_machine.errors import PrecondicionNoCumplida
from app.state_machine.repositories import (
    tiene_documento,
    tiene_garantia,
    tiene_garantia_cumplimiento_vigente,
)


# --------------------------------------------------------------------------- utilidades
def combinar(*guards):
    def _guard(ctx: ContextoTransicion) -> None:
        for g in guards:
            g(ctx)

    return _guard


# --------------------------------------------------------------------------- guards contrato
def g_completitud_ok(ctx: ContextoTransicion) -> None:
    if ctx.extra.get("completitud_ok", True) is not True:
        raise PrecondicionNoCumplida("La validación automática de completitud no está OK")


def g_completitud_falla(ctx: ContextoTransicion) -> None:
    if ctx.extra.get("completitud_ok", True) is True:
        raise PrecondicionNoCumplida(
            "Esta transición solo aplica cuando la validación de completitud falla"
        )


def g_requiere_gerencia(ctx: ContextoTransicion) -> None:
    if not ctx.entidad.requiere_aprobacion_gerencia:
        raise PrecondicionNoCumplida("El contrato no requiere aprobación de Gerencia")


def g_no_requiere_gerencia(ctx: ContextoTransicion) -> None:
    if ctx.entidad.requiere_aprobacion_gerencia:
        raise PrecondicionNoCumplida("El contrato requiere aprobación de Gerencia primero")


def g_abogado_asignado(ctx: ContextoTransicion) -> None:
    if ctx.entidad.abogado_id is None:
        raise PrecondicionNoCumplida("Debe asignarse un abogado responsable (Admisibilidad II)")


def g_borrador_cargado(ctx: ContextoTransicion) -> None:
    if ctx.extra.get("borrador_cargado"):
        return
    if tiene_documento(ctx.session, ctx.entidad_tipo, ctx.entidad.id, DocumentoTipo.borrador):
        return
    raise PrecondicionNoCumplida("No hay borrador de contrato cargado")


def g_visacion_ok(ctx: ContextoTransicion) -> None:
    if ctx.extra.get("visacion_interna_ok", True) is not True:
        raise PrecondicionNoCumplida("Falta la visación interna del texto contractual")
    if ctx.entidad.requiere_visacion_contraparte and not ctx.extra.get("visacion_contraparte_ok", False):
        raise PrecondicionNoCumplida("Falta la visación con la contraparte externa")


def g_garantia_si_requiere(ctx: ContextoTransicion) -> None:
    if ctx.entidad.requiere_garantia and not tiene_garantia_cumplimiento_vigente(
        ctx.session, ctx.entidad_tipo, ctx.entidad.id
    ):
        raise PrecondicionNoCumplida(
            "El contrato exige una garantía de cumplimiento vigente antes de la firma"
        )


def g_garantia_cumplimiento_vigente(ctx: ContextoTransicion) -> None:
    if not tiene_garantia_cumplimiento_vigente(ctx.session, ctx.entidad_tipo, ctx.entidad.id):
        raise PrecondicionNoCumplida(
            "Debe constituirse la garantía de fiel cumplimiento antes de la firma (Gate 2)"
        )


def g_documento_firmado(ctx: ContextoTransicion) -> None:
    if ctx.extra.get("documento_firmado"):
        return
    if tiene_documento(
        ctx.session, ctx.entidad_tipo, ctx.entidad.id, DocumentoTipo.contrato_firmado
    ):
        return
    raise PrecondicionNoCumplida("No hay documento de contrato firmado cargado")


def g_puede_pasar_a_vigente(ctx: ContextoTransicion) -> None:
    e = ctx.entidad
    if e.administrador_id is None:
        raise PrecondicionNoCumplida("Falta designar al administrador del contrato")
    if not e.vigencia_indefinida and e.fecha_fin_vigencia is None:
        raise PrecondicionNoCumplida("Falta la fecha de fin de vigencia (o marcar vigencia indefinida)")


def g_formato_no_modificado(ctx: ContextoTransicion) -> None:
    from app.models.core import FormatoEstandar  # import local para evitar ciclos

    e = ctx.entidad
    if e.formato_id is None:
        raise PrecondicionNoCumplida("Línea B requiere un formato estándar seleccionado")
    formato = ctx.session.get(FormatoEstandar, e.formato_id)
    checksum = ctx.extra.get("documento_checksum")
    if formato is None or checksum is None or checksum != formato.checksum_base:
        raise PrecondicionNoCumplida(
            "El clausulado del formato fue modificado: el checksum no coincide con el estándar"
        )


# --------------------------------------------------------------------------- guards licitación
def g_informe_riesgos(ctx: ContextoTransicion) -> None:
    if ctx.entidad.informe_riesgos_id is None and not ctx.extra.get("informe_riesgos_ok"):
        raise PrecondicionNoCumplida("Falta el Informe de Riesgos y Validación Final")


def g_oferta_lista(ctx: ContextoTransicion) -> None:
    if not (ctx.extra.get("oferta_tecnica_ok") and ctx.extra.get("oferta_economica_ok")):
        raise PrecondicionNoCumplida("Falta completar la oferta técnica y/o la propuesta económica")
    if ctx.entidad.exige_garantia_seriedad and not tiene_garantia(
        ctx.session, ctx.entidad_tipo, ctx.entidad.id, GarantiaTipo.seriedad_oferta
    ):
        raise PrecondicionNoCumplida("Las bases exigen garantía de seriedad de la oferta")


def g_coherente_con_oferta(ctx: ContextoTransicion) -> None:
    if ctx.extra.get("coherente_con_oferta") is not True:
        raise PrecondicionNoCumplida(
            "El contrato no fue validado como coherente con la oferta (multas, plazos, reajustes)"
        )


def g_analisis_interno(ctx: ContextoTransicion) -> None:
    if not ctx.extra.get("analisis_interno"):
        raise PrecondicionNoCumplida(
            "Debe registrarse el análisis interno para mejora continua (licitación no adjudicada)"
        )


# --------------------------------------------------------------------------- efectos
def ef_fecha_aprobacion_jefatura(ctx: ContextoTransicion) -> None:
    ctx.entidad.fecha_aprobacion_jefatura = ctx.fecha.date()


def ef_fecha_admisibilidad(ctx: ContextoTransicion) -> None:
    ctx.entidad.fecha_admisibilidad = ctx.fecha.date()


def ef_fecha_visacion(ctx: ContextoTransicion) -> None:
    ctx.entidad.fecha_visacion = ctx.fecha.date()


def ef_fecha_firma(ctx: ContextoTransicion) -> None:
    ctx.entidad.fecha_firma = ctx.fecha.date()


def ef_fecha_integracion(ctx: ContextoTransicion) -> None:
    ctx.entidad.fecha_integracion = ctx.fecha.date()


def ef_iniciar_vigencia(ctx: ContextoTransicion) -> None:
    e = ctx.entidad
    if e.fecha_inicio_vigencia is None:
        e.fecha_inicio_vigencia = ctx.fecha.date()
    ctx.session.add(
        Hito(
            contrato_id=e.id,
            tipo=HitoTipo.inicio_ejecucion,
            nombre="Inicio de ejecución contractual",
            fecha_planificada=e.fecha_inicio_vigencia or ctx.fecha.date(),
            fecha_real=ctx.fecha.date(),
            estado=HitoEstado.cumplido,
        )
    )


def ef_renovacion(ctx: ContextoTransicion) -> None:
    nueva = ctx.extra.get("nueva_fecha_fin")
    if not isinstance(nueva, date):
        raise PrecondicionNoCumplida("Debe indicarse 'nueva_fecha_fin' (date) para renovar")
    ctx.entidad.fecha_fin_vigencia = nueva
    ctx.session.add(
        Hito(
            contrato_id=ctx.entidad.id,
            tipo=HitoTipo.renovacion,
            nombre="Renovación de vigencia",
            fecha_planificada=ctx.fecha.date(),
            fecha_real=ctx.fecha.date(),
            estado=HitoEstado.cumplido,
        )
    )


def ef_terminar(ctx: ContextoTransicion) -> None:
    ctx.entidad.fecha_cierre = ctx.fecha.date()


def ef_adjudicada(ctx: ContextoTransicion) -> None:
    ctx.entidad.resultado = LicitacionResultado.adjudicado
    ctx.entidad.fecha_resultado = ctx.fecha.date()


def ef_no_adjudicada(ctx: ContextoTransicion) -> None:
    ctx.entidad.resultado = LicitacionResultado.no_adjudicado
    ctx.entidad.fecha_resultado = ctx.fecha.date()
    ctx.entidad.analisis_interno = str(ctx.extra.get("analisis_interno"))


def ef_desierta(ctx: ContextoTransicion) -> None:
    ctx.entidad.resultado = LicitacionResultado.desierto
    ctx.entidad.fecha_resultado = ctx.fecha.date()


def ef_desistida(ctx: ContextoTransicion) -> None:
    ctx.entidad.resultado = LicitacionResultado.desistido
    ctx.entidad.fecha_resultado = ctx.fecha.date()
