"""Auditoría a nivel sistema: historial de eventos de todos los contratos
y licitaciones, exclusivo de admin_sistema."""
from __future__ import annotations

from app.enums import EstadoContrato, LineaContrato, Rol
from app.services.auditoria import historial_global
from app.services.auth import hash_password
from app.services.contratos import crear_contrato
from app.state_machine import MotorEstados
from tests._helpers import avanzar_a


def test_historial_global_incluye_todos_los_contratos(session, usuarios, unidad, contraparte):
    c1 = crear_contrato(
        session, codigo="CT-AUD-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    c2 = crear_contrato(
        session, codigo="CT-AUD-2", linea=LineaContrato.A_regular, objeto="y",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c1, usuarios, EstadoContrato.aprobacion_jefatura)
    session.commit()

    eventos = historial_global(session)
    codigos = {e["codigo"] for e in eventos}
    assert "CT-AUD-1" in codigos and "CT-AUD-2" in codigos

    solo_jefatura = historial_global(session, usuario_id=usuarios[Rol.unidad_solicitante].id)
    assert all(e["usuario_id"] == usuarios[Rol.unidad_solicitante].id for e in solo_jefatura)
    assert len(solo_jefatura) >= 1


def test_pagina_auditoria_solo_admin_sistema(api, session, usuarios, unidad, contraparte):
    crear_contrato(
        session, codigo="CT-AUD-WEB", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()

    legal = usuarios[Rol.legal]
    legal.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": legal.email, "password": "clave12345"})
    r = api.get("/panel/auditoria", follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]

    admin = usuarios[Rol.admin_sistema]
    admin.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": admin.email, "password": "clave12345"})
    r = api.get("/panel/auditoria")
    assert r.status_code == 200
    assert "CT-AUD-WEB" in r.text
