"""Motor de alertas (calculadas al vuelo)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from app.enums import (
    EstadoContrato,
    GarantiaEstado,
    GarantiaInstrumento,
    GarantiaTipo,
    HitoEstado,
    HitoTipo,
    LineaContrato,
    Moneda,
    Rol,
)
from app.models.contrato import Garantia, Hito
from app.services.alertas import calcular_alertas, resumen_alertas
from app.services.contratos import crear_contrato
from app.state_machine import MotorEstados

HOY = date.today()


def test_alertas_de_cartera(session, cartera):
    session.add(Garantia(
        entidad_tipo="contrato", entidad_id=cartera["VIG"], tipo=GarantiaTipo.fiel_cumplimiento,
        instrumento=GarantiaInstrumento.boleta_bancaria, monto=1, moneda=Moneda.CLP,
        fecha_emision=date(2024, 1, 1), fecha_vencimiento=HOY - timedelta(days=5),
        estado=GarantiaEstado.vigente,
    ))
    session.add(Hito(
        contrato_id=cartera["VIG"], tipo=HitoTipo.entregable, nombre="Entrega X",
        fecha_planificada=HOY - timedelta(days=3), estado=HitoEstado.pendiente,
    ))
    session.commit()

    res = calcular_alertas(session)
    tipos = [a["tipo"] for a in res]
    assert tipos.count("contrato_vencido") == 1
    assert tipos.count("contrato_por_vencer") == 2      # C-PORVENCER + C-RENOV
    assert tipos.count("renovacion_proxima") == 1       # C-RENOV
    assert tipos.count("garantia_vencida") == 1
    assert tipos.count("hito_atrasado") == 1
    assert res[0]["nivel"] == "critica"                 # ordenado por severidad

    r = resumen_alertas(session)
    assert r["total"] == len(res)
    assert r["por_nivel"].get("critica", 0) >= 3


def test_solicitud_estancada_en_aclaraciones(session, usuarios, unidad, contraparte):
    c = crear_contrato(
        session, codigo="C-ACL", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    motor = MotorEstados(session)
    motor.transicionar_contrato(c, EstadoContrato.aprobacion_jefatura, usuario=usuarios[Rol.unidad_solicitante])
    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.jefatura])
    motor.transicionar_contrato(c, EstadoContrato.aclaraciones, usuario=usuarios[Rol.legal], comentario="falta info")
    c.estado_desde = datetime.utcnow() - timedelta(days=15)
    session.commit()

    res = calcular_alertas(session, tipo="solicitud_estancada")
    assert len(res) == 1
    assert res[0]["contrato_codigo"] == "C-ACL"


def test_api_y_web_alertas(api, cartera):
    r = api.get("/alertas")
    assert r.status_code == 200
    assert len(r.json()) >= 3
    assert api.get("/alertas", params={"tipo": "contrato_vencido"}).json()[0]["nivel"] == "critica"
    assert api.get("/alertas", params={"nivel": "critica"}).json()

    resumen = api.get("/alertas/resumen").json()
    assert resumen["total"] >= 3

    w = api.get("/panel/alertas")
    assert w.status_code == 200 and "C-VENCIDO" in w.text
    assert "alerta" in api.get("/panel").text.lower()
