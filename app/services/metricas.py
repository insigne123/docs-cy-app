"""Métricas de proceso derivadas de la trazabilidad (EventoEstado)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import median
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import EstadoContrato
from app.models.contrato import Contrato
from app.models.evento import EventoEstado


def _media(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def metricas_proceso(session: Session, *, hoy: Optional[date] = None) -> dict:
    hoy = hoy or date.today()

    eventos = list(
        session.scalars(
            select(EventoEstado)
            .where(EventoEstado.entidad_tipo == "contrato")
            .order_by(EventoEstado.entidad_id, EventoEstado.fecha, EventoEstado.id)
        )
    )
    por_contrato: dict[int, list[EventoEstado]] = defaultdict(list)
    for e in eventos:
        por_contrato[e.entidad_id].append(e)

    permanencia: dict[str, list[int]] = defaultdict(list)
    throughput: dict[str, int] = defaultdict(int)
    descartes = 0
    for evs in por_contrato.values():
        for actual, siguiente in zip(evs, evs[1:]):
            dias = (siguiente.fecha - actual.fecha).days
            if dias >= 0:
                permanencia[actual.estado_destino].append(dias)
        for e in evs:
            if e.estado_destino == EstadoContrato.vigente.value:
                throughput[e.fecha.strftime("%Y-%m")] += 1
                break
            if e.estado_destino == EstadoContrato.descartado.value:
                descartes += 1
                break

    resumen_estados = sorted(
        (
            {
                "estado": estado,
                "n": len(dias),
                "dias_promedio": round(_media(dias), 1),
                "dias_mediana": round(median(dias), 1) if dias else 0,
                "dias_max": max(dias) if dias else 0,
            }
            for estado, dias in permanencia.items()
        ),
        key=lambda r: r["dias_promedio"],
        reverse=True,
    )

    total = session.scalar(select(func.count()).select_from(Contrato)) or 0
    en_aclaraciones = (
        session.scalar(
            select(func.count()).select_from(Contrato).where(
                Contrato.estado == EstadoContrato.aclaraciones
            )
        )
        or 0
    )
    return {
        "generado_al": hoy,
        "total_contratos": total,
        "descartes": descartes,
        "tasa_descarte": round(descartes / total, 3) if total else 0.0,
        "en_aclaraciones": en_aclaraciones,
        "cuello_de_botella": resumen_estados[0]["estado"] if resumen_estados else None,
        "permanencia_por_estado": resumen_estados,
        "throughput_mensual": [
            {"periodo": p, "a_vigente": n} for p, n in sorted(throughput.items())
        ],
    }
