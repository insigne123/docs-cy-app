"""Gráfico de tendencia del tablero: contratos ingresados por mes."""
from __future__ import annotations

from datetime import date

from app.enums import LineaContrato, Rol
from app.services.contratos import crear_contrato
from app.services.dashboard import tendencia_mensual


def test_tendencia_mensual_cuenta_por_mes_y_rellena_meses_vacios(session, usuarios, unidad, contraparte):
    hoy = date(2026, 6, 15)
    crear_contrato(
        session, codigo="CT-TEND-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
        fecha_ingreso=date(2026, 6, 1),
    )
    crear_contrato(
        session, codigo="CT-TEND-2", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
        fecha_ingreso=date(2026, 6, 20),
    )
    crear_contrato(
        session, codigo="CT-TEND-3", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
        fecha_ingreso=date(2025, 6, 1),  # fuera de la ventana de 12 meses
    )
    session.commit()

    t = tendencia_mensual(session, meses=12, hoy=hoy)
    assert len(t) == 12
    assert t[-1]["periodo"] == "2026-06"
    assert t[-1]["cantidad"] == 2
    assert t[-1]["pct"] == 100
    assert t[0]["periodo"] == "2025-07"
    # Un mes sin contratos ingresados sigue apareciendo, en 0.
    assert any(m["cantidad"] == 0 for m in t[:-1])


def test_tablero_muestra_la_tendencia(api, session, usuarios, cartera):
    r = api.get("/panel")
    assert r.status_code == 200
    assert "Contratos ingresados por mes" in r.text
