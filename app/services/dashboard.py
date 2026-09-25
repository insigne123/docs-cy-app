"""Datos del panel: contratos agrupados por mes, indicadores y semáforo de vigencia."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import (
    ESTADOS_CONTRATO_TERMINALES,
    NOMBRES_LINEA,
    EstadoContrato,
    LineaContrato,
    TipoRenovacion,
    nombre_linea,
)
from app.models.contrato import Contrato
from app.models.core import Contraparte, Unidad, Usuario
from app.services.parametros import obtener_parametro

AGRUPACIONES = {
    "ingreso": "fecha_ingreso",
    "firma": "fecha_firma",
    "vencimiento": "fecha_fin_vigencia",
}

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

_TERMINALES = frozenset(e.value for e in ESTADOS_CONTRATO_TERMINALES)


def _umbrales(session: Session) -> list[int]:
    crudo = obtener_parametro(session, "alerta_umbrales_dias", "90,60,30") or "90,60,30"
    try:
        return sorted({int(x) for x in crudo.split(",") if x.strip()}, reverse=True)
    except ValueError:
        return [90, 60, 30]


def _semaforo(contrato: Contrato, hoy: date, umbrales: list[int]) -> tuple[str, Optional[str], Optional[int]]:
    """Devuelve (semaforo, nivel_alerta, dias_para_vencer)."""
    estado = contrato.estado.value
    if estado in _TERMINALES:
        return "cerrado", None, None
    if estado != EstadoContrato.vigente.value:
        return "en_tramite", None, None
    if contrato.vigencia_indefinida:
        return "vigente", None, None
    if contrato.fecha_fin_vigencia is None:
        return "sin_vigencia", None, None

    dias = (contrato.fecha_fin_vigencia - hoy).days
    if dias < 0:
        return "vencido", "critica", dias

    u_max = umbrales[0] if umbrales else 90
    if dias > u_max:
        return "vigente", None, dias

    nivel = "informativa"
    for u in sorted(umbrales):  # 30, 60, 90 -> el más chico que aún cubre 'dias'
        if dias <= u:
            nivel = {30: "urgente", 60: "atencion", 90: "informativa"}.get(u, "informativa")
            break
    semaforo = "por_vencer"
    if contrato.tipo_renovacion != TipoRenovacion.sin_renovacion:
        semaforo = "en_renovacion"
    return semaforo, nivel, dias


def semaforo_de(
    session: Session, contrato: Contrato, hoy: Optional[date] = None
) -> tuple[str, Optional[str], Optional[int]]:
    """(semaforo, nivel_alerta, dias_para_vencer) para un contrato individual."""
    return _semaforo(contrato, hoy or date.today(), _umbrales(session))


def _periodo(f: Optional[date]) -> tuple[str, str]:
    if f is None:
        return "sin_fecha", "Sin fecha"
    return f.strftime("%Y-%m"), f"{MESES_ES[f.month].capitalize()} {f.year}"


def _dec(v: Optional[Decimal]) -> Optional[str]:
    return None if v is None else f"{Decimal(v):.2f}"


def _acumular_monto(acc: dict[str, Decimal], contrato: Contrato) -> None:
    if contrato.monto is not None and contrato.moneda is not None:
        acc[contrato.moneda.value] = acc.get(contrato.moneda.value, Decimal(0)) + Decimal(contrato.monto)


def construir_dashboard(
    session: Session,
    *,
    agrupacion: str = "vencimiento",
    linea: Optional[str] = None,
    estado: Optional[str] = None,
    unidad_id: Optional[int] = None,
    administrador_id: Optional[int] = None,
    contraparte_id: Optional[int] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    hoy: Optional[date] = None,
) -> dict:
    if agrupacion not in AGRUPACIONES:
        agrupacion = "vencimiento"
    campo_fecha = AGRUPACIONES[agrupacion]
    hoy = hoy or date.today()
    umbrales = _umbrales(session)

    stmt = select(Contrato)
    if linea:
        stmt = stmt.where(Contrato.linea == LineaContrato(linea))
    if estado:
        stmt = stmt.where(Contrato.estado == EstadoContrato(estado))
    if unidad_id:
        stmt = stmt.where(Contrato.unidad_solicitante_id == unidad_id)
    if administrador_id:
        stmt = stmt.where(Contrato.administrador_id == administrador_id)
    if contraparte_id:
        stmt = stmt.where(Contrato.contraparte_id == contraparte_id)
    contratos = list(session.scalars(stmt.order_by(Contrato.codigo)))

    nombres_cp = {c.id: c.razon_social for c in session.scalars(select(Contraparte))}
    nombres_un = {u.id: u.nombre for u in session.scalars(select(Unidad))}
    nombres_us = {u.id: u.nombre for u in session.scalars(select(Usuario))}

    ind_linea: dict[str, int] = {}
    ind_estado: dict[str, int] = {}
    monto_total: dict[str, Decimal] = {}
    vigentes = por_vencer = vencidos = en_renovacion = 0

    grupos: dict[str, dict] = {}
    for c in contratos:
        fecha_grupo = getattr(c, campo_fecha)
        if desde and (fecha_grupo is None or fecha_grupo < desde):
            continue
        if hasta and (fecha_grupo is None or fecha_grupo > hasta):
            continue

        semaforo, nivel, dias = _semaforo(c, hoy, umbrales)
        ind_linea[c.linea.value] = ind_linea.get(c.linea.value, 0) + 1
        ind_estado[c.estado.value] = ind_estado.get(c.estado.value, 0) + 1
        _acumular_monto(monto_total, c)
        if semaforo == "vigente":
            vigentes += 1
        elif semaforo in ("por_vencer", "en_renovacion"):
            por_vencer += 1
            if semaforo == "en_renovacion":
                en_renovacion += 1
        elif semaforo == "vencido":
            vencidos += 1

        periodo, etiqueta = _periodo(fecha_grupo)
        g = grupos.setdefault(
            periodo, {"periodo": periodo, "etiqueta": etiqueta, "contratos": [], "_monto": {}}
        )
        _acumular_monto(g["_monto"], c)
        g["contratos"].append(
            {
                "id": c.id,
                "codigo": c.codigo,
                "linea": c.linea.value,
                "linea_nombre": nombre_linea(c.linea.value),
                "estado": c.estado.value,
                "objeto": c.objeto,
                "contraparte": nombres_cp.get(c.contraparte_id),
                "unidad": nombres_un.get(c.unidad_solicitante_id),
                "administrador": nombres_us.get(c.administrador_id),
                "monto": _dec(c.monto),
                "moneda": c.moneda.value if c.moneda else None,
                "fecha_ingreso": c.fecha_ingreso,
                "fecha_firma": c.fecha_firma,
                "fecha_inicio_vigencia": c.fecha_inicio_vigencia,
                "fecha_fin_vigencia": c.fecha_fin_vigencia,
                "vigencia_indefinida": c.vigencia_indefinida,
                "tipo_renovacion": c.tipo_renovacion.value,
                "dias_para_vencer": dias,
                "semaforo": semaforo,
                "nivel_alerta": nivel,
            }
        )

    def _clave(periodo: str) -> tuple:
        return (1, "") if periodo == "sin_fecha" else (0, periodo)

    lista_grupos = []
    for periodo in sorted(grupos, key=_clave):
        g = grupos[periodo]
        lista_grupos.append(
            {
                "periodo": g["periodo"],
                "etiqueta": g["etiqueta"],
                "cantidad": len(g["contratos"]),
                "monto_total": {m: f"{v:.2f}" for m, v in g.pop("_monto").items()},
                "contratos": g["contratos"],
            }
        )

    total = sum(len(g["contratos"]) for g in lista_grupos)
    return {
        "generado": datetime.utcnow(),
        "agrupacion": agrupacion,
        "hoy": hoy,
        "filtros": {
            "linea": linea,
            "estado": estado,
            "unidad_id": unidad_id,
            "administrador_id": administrador_id,
            "contraparte_id": contraparte_id,
            "desde": desde,
            "hasta": hasta,
        },
        "indicadores": {
            "total": total,
            "por_linea": ind_linea,
            "por_estado": ind_estado,
            "vigentes": vigentes,
            "por_vencer": por_vencer,
            "vencidos": vencidos,
            "en_renovacion": en_renovacion,
            "monto_total": {m: f"{v:.2f}" for m, v in monto_total.items()},
        },
        "grupos": lista_grupos,
    }


def listar_contratos(session: Session, **filtros) -> list[dict]:
    """Todos los contratos (cualquier estado) en una sola lista plana ordenada
    por código — para el módulo de Listado de Contratos. A diferencia de
    construir_dashboard(), no agrupa por mes; acepta los mismos filtros
    (linea, estado, unidad_id, administrador_id, contraparte_id, desde, hasta)."""
    filtros.pop("agrupacion", None)
    datos = construir_dashboard(session, agrupacion="vencimiento", **filtros)
    filas = [c for g in datos["grupos"] for c in g["contratos"]]
    filas.sort(key=lambda c: c["codigo"])
    return filas


def listar_vigentes_para_gestion(session: Session, hoy: Optional[date] = None) -> list[dict]:
    """Contratos en estado 'vigente', ordenados por urgencia (vencidos y por vencer
    primero; indefinidos al final) — para el módulo de Gestión de Vigencias."""
    datos = construir_dashboard(session, agrupacion="vencimiento", estado=EstadoContrato.vigente.value, hoy=hoy)
    filas = [c for g in datos["grupos"] for c in g["contratos"]]
    filas.sort(key=lambda c: (c["dias_para_vencer"] is None, c["dias_para_vencer"] if c["dias_para_vencer"] is not None else 0))
    return filas


def opciones_filtros(session: Session) -> dict:
    return {
        "lineas": [{"value": e.value, "nombre": NOMBRES_LINEA[e.value]} for e in LineaContrato],
        "estados": [e.value for e in EstadoContrato],
        "agrupaciones": list(AGRUPACIONES),
        "unidades": [
            {"id": u.id, "nombre": u.nombre}
            for u in session.scalars(select(Unidad).order_by(Unidad.nombre))
        ],
        "contrapartes": [
            {"id": c.id, "nombre": c.razon_social}
            for c in session.scalars(select(Contraparte).order_by(Contraparte.razon_social))
        ],
        "administradores": [
            {"id": u.id, "nombre": u.nombre}
            for u in session.scalars(select(Usuario).order_by(Usuario.nombre))
        ],
    }
