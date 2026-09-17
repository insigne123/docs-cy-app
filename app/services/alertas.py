"""Motor de alertas: se calculan al vuelo, no se almacenan (docs/02 §5.10)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import (
    ESTADOS_CONTRATO_TERMINALES,
    EstadoContrato,
    GarantiaEstado,
    HitoEstado,
    TipoRenovacion,
)
from app.models.contrato import Contrato, Garantia, Hito
from app.services.parametros import obtener_parametro

_TERMINALES = frozenset(e.value for e in ESTADOS_CONTRATO_TERMINALES)

TIPOS_ALERTA = [
    "contrato_vencido",
    "contrato_por_vencer",
    "renovacion_proxima",
    "garantia_vencida",
    "garantia_por_vencer",
    "hito_atrasado",
    "solicitud_estancada",
]
_ORDEN_NIVEL = {"critica": 0, "urgente": 1, "atencion": 2, "informativa": 3}


def _umbrales(session: Session) -> list[int]:
    crudo = obtener_parametro(session, "alerta_umbrales_dias", "90,60,30") or "90,60,30"
    try:
        return sorted({int(x) for x in crudo.split(",") if x.strip()}, reverse=True)
    except ValueError:
        return [90, 60, 30]


def _nivel(dias: int, umbrales: list[int]) -> str:
    if dias < 0:
        return "critica"
    for u in sorted(umbrales):
        if dias <= u:
            return {30: "urgente", 60: "atencion", 90: "informativa"}.get(u, "informativa")
    return "informativa"


@dataclass
class Alerta:
    tipo: str
    nivel: str
    entidad_tipo: str
    entidad_id: int
    contrato_id: Optional[int]
    contrato_codigo: Optional[str]
    titulo: str
    detalle: str
    fecha_referencia: Optional[date]
    dias: Optional[int]


def calcular_alertas(
    session: Session,
    *,
    hoy: Optional[date] = None,
    tipo: Optional[str] = None,
    nivel: Optional[str] = None,
) -> list[dict]:
    hoy = hoy or date.today()
    umbrales = _umbrales(session)
    u_max = umbrales[0] if umbrales else 90
    dias_estancada = int(obtener_parametro(session, "aclaraciones_dias_alerta", "10") or 10)

    contratos = list(session.scalars(select(Contrato)))
    cod = {c.id: c.codigo for c in contratos}
    out: list[Alerta] = []

    for c in contratos:
        est = c.estado.value
        if (
            est == EstadoContrato.vigente.value
            and not c.vigencia_indefinida
            and c.fecha_fin_vigencia is not None
        ):
            d = (c.fecha_fin_vigencia - hoy).days
            if d < 0:
                out.append(Alerta(
                    "contrato_vencido", "critica", "contrato", c.id, c.id, c.codigo,
                    f"Contrato {c.codigo} vencido",
                    f"Venció el {c.fecha_fin_vigencia} ({-d} días atrás)",
                    c.fecha_fin_vigencia, d,
                ))
            elif d <= u_max:
                out.append(Alerta(
                    "contrato_por_vencer", _nivel(d, umbrales), "contrato", c.id, c.id, c.codigo,
                    f"Contrato {c.codigo} por vencer",
                    f"Vence el {c.fecha_fin_vigencia} (en {d} días)",
                    c.fecha_fin_vigencia, d,
                ))
                if c.tipo_renovacion != TipoRenovacion.sin_renovacion:
                    out.append(Alerta(
                        "renovacion_proxima", _nivel(d, umbrales), "contrato", c.id, c.id, c.codigo,
                        f"Renovación próxima de {c.codigo}",
                        f"Renovación {c.tipo_renovacion.value}; aviso {c.aviso_previo_dias} d; "
                        f"vence el {c.fecha_fin_vigencia}",
                        c.fecha_fin_vigencia, d,
                    ))

        if est == EstadoContrato.aclaraciones.value and c.estado_desde is not None:
            dd = (hoy - c.estado_desde.date()).days
            if dd >= dias_estancada:
                out.append(Alerta(
                    "solicitud_estancada",
                    "urgente" if dd >= dias_estancada * 2 else "atencion",
                    "contrato", c.id, c.id, c.codigo,
                    f"Solicitud {c.codigo} estancada en aclaraciones",
                    f"{dd} días en 'aclaraciones' (umbral {dias_estancada})",
                    c.estado_desde.date(), -dd,
                ))

    garantias = session.scalars(
        select(Garantia).where(
            Garantia.entidad_tipo == "contrato", Garantia.estado == GarantiaEstado.vigente
        )
    )
    for g in garantias:
        d = (g.fecha_vencimiento - hoy).days
        cc = cod.get(g.entidad_id)
        if d < 0:
            out.append(Alerta(
                "garantia_vencida", "critica", "garantia", g.id, g.entidad_id, cc,
                f"Garantía vencida ({cc or 'contrato ' + str(g.entidad_id)})",
                f"{g.tipo.value} venció el {g.fecha_vencimiento} ({-d} días atrás)",
                g.fecha_vencimiento, d,
            ))
        elif d <= u_max:
            out.append(Alerta(
                "garantia_por_vencer", _nivel(d, umbrales), "garantia", g.id, g.entidad_id, cc,
                f"Garantía por vencer ({cc or 'contrato ' + str(g.entidad_id)})",
                f"{g.tipo.value} vence el {g.fecha_vencimiento} (en {d} días)",
                g.fecha_vencimiento, d,
            ))

    hitos = session.scalars(select(Hito).where(Hito.estado == HitoEstado.pendiente))
    for h in hitos:
        if h.fecha_real is None and h.fecha_planificada < hoy:
            d = (h.fecha_planificada - hoy).days
            out.append(Alerta(
                "hito_atrasado", "critica" if d < 0 else _nivel(d, umbrales),
                "hito", h.id, h.contrato_id, cod.get(h.contrato_id),
                f"Hito atrasado: {h.nombre}",
                f"Planificado {h.fecha_planificada} ({-d} días de atraso)",
                h.fecha_planificada, d,
            ))

    res = [asdict(a) for a in out]
    if tipo:
        res = [a for a in res if a["tipo"] == tipo]
    if nivel:
        res = [a for a in res if a["nivel"] == nivel]
    res.sort(key=lambda a: (_ORDEN_NIVEL.get(a["nivel"], 9), a["dias"] if a["dias"] is not None else 0))
    return res


def resumen_alertas(session: Session, *, hoy: Optional[date] = None) -> dict:
    alertas = calcular_alertas(session, hoy=hoy)
    por_tipo: dict[str, int] = {}
    por_nivel: dict[str, int] = {}
    for a in alertas:
        por_tipo[a["tipo"]] = por_tipo.get(a["tipo"], 0) + 1
        por_nivel[a["nivel"]] = por_nivel.get(a["nivel"], 0) + 1
    return {"total": len(alertas), "por_tipo": por_tipo, "por_nivel": por_nivel}
