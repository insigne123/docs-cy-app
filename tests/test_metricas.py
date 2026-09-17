"""Métricas de proceso a partir de la trazabilidad."""
from __future__ import annotations

from app.services.metricas import metricas_proceso


def test_metricas_proceso(session, cartera):
    m = metricas_proceso(session)
    assert m["total_contratos"] == 5
    assert m["descartes"] == 0
    # 4 contratos de la cartera llegaron a 'vigente'
    assert sum(t["a_vigente"] for t in m["throughput_mensual"]) == 4
    estados = {r["estado"] for r in m["permanencia_por_estado"]}
    assert {"elaboracion", "ingreso"} <= estados
    assert m["cuello_de_botella"] is not None


def test_metricas_con_descarte(session, cartera, usuarios, unidad):
    from app.enums import EstadoContrato, LineaContrato, Rol
    from app.services.contratos import crear_contrato
    from app.state_machine import MotorEstados

    solicitante = usuarios[Rol.unidad_solicitante]
    c = crear_contrato(
        session, codigo="C-DESC", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=solicitante,
    )
    MotorEstados(session).transicionar_contrato(
        c, EstadoContrato.descartado, usuario=solicitante, comentario="no viable"
    )
    session.commit()

    m = metricas_proceso(session)
    assert m["descartes"] == 1
    assert m["total_contratos"] == 6
    assert round(m["tasa_descarte"], 3) == round(1 / 6, 3)


def test_api_y_web_metricas(api, cartera):
    r = api.get("/metricas")
    assert r.status_code == 200
    assert r.json()["total_contratos"] == 5

    w = api.get("/panel/metricas")
    assert w.status_code == 200
    assert "Permanencia por estado" in w.text
