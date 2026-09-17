"""Parámetros de configuración del sistema."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.core import Parametro

PARAMETROS_POR_DEFECTO: dict[str, tuple[str, str]] = {
    "alerta_umbrales_dias": ("90,60,30", "Niveles de alerta (días) antes de vencimiento/renovación"),
    "monto_aprobacion_gerencia_clp": ("50000000", "Monto CLP desde el cual se exige aprobación de Gerencia"),
    "aclaraciones_dias_alerta": ("10", "Días en 'aclaraciones' tras los cuales se marca solicitud estancada"),
    "moneda_base": ("CLP", "Moneda para totalizar el dashboard"),
    "dashboard_agrupacion_default": ("vencimiento", "Criterio inicial del selector (ingreso/firma/vencimiento)"),
}


def sembrar_parametros(session: Session) -> None:
    """Inserta los parámetros que aún no existan. Idempotente."""
    existentes = {p.clave for p in session.query(Parametro).all()}
    for clave, (valor, desc) in PARAMETROS_POR_DEFECTO.items():
        if clave not in existentes:
            session.add(Parametro(clave=clave, valor=valor, descripcion=desc))
    session.flush()


def obtener_parametro(session: Session, clave: str, default: str | None = None) -> str | None:
    p = session.get(Parametro, clave)
    if p is not None:
        return p.valor
    if default is not None:
        return default
    return PARAMETROS_POR_DEFECTO.get(clave, (None, None))[0]
