"""Bandeja 'Mis tareas': contratos y licitaciones accionables por rol."""
from __future__ import annotations

from app.enums import EstadoContrato, LineaContrato, Rol
from app.services.auth import hash_password
from app.services.contratos import crear_contrato
from app.services.licitaciones import crear_licitacion
from app.services.tareas import tareas_pendientes
from app.state_machine import MotorEstados
from tests._helpers import avanzar_a


def test_tareas_pendientes_contrato_por_rol(session, usuarios, unidad, contraparte):
    c = crear_contrato(
        session, codigo="CT-TAREA", linea=LineaContrato.A_regular, objeto="Objeto de prueba",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    avanzar_a(MotorEstados(session), c, usuarios, EstadoContrato.aprobacion_jefatura)
    session.commit()

    # A4/A5 (aprobacion_jefatura -> ...) son exclusivas de Jefatura.
    t_jefatura = tareas_pendientes(session, usuarios[Rol.jefatura])
    assert any(x["codigo"] == "CT-TAREA" for x in t_jefatura["contratos"])

    t_legal = tareas_pendientes(session, usuarios[Rol.legal])
    assert not any(x["codigo"] == "CT-TAREA" for x in t_legal["contratos"])


def test_tareas_pendientes_licitacion_recien_creada(session, usuarios, unidad, contraparte):
    lic = crear_licitacion(
        session, codigo="LIC-TAREA", objeto="Licitación de prueba",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()

    # L1 (ingreso_antecedentes -> examen_admisibilidad) es exclusiva de admin_licitaciones.
    t = tareas_pendientes(session, usuarios[Rol.admin_licitaciones])
    assert any(x["codigo"] == "LIC-TAREA" for x in t["licitaciones"])

    t_tecnica = tareas_pendientes(session, usuarios[Rol.tecnica])
    assert not any(x["codigo"] == "LIC-TAREA" for x in t_tecnica["licitaciones"])


def test_pagina_mis_tareas_requiere_login_y_muestra_lo_pendiente(api, session, usuarios, unidad, contraparte):
    c = crear_contrato(
        session, codigo="CT-TAREA-WEB", linea=LineaContrato.A_regular, objeto="Objeto web",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    avanzar_a(MotorEstados(session), c, usuarios, EstadoContrato.aprobacion_jefatura)
    session.commit()

    r = api.get("/panel/tareas", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")

    jefatura = usuarios[Rol.jefatura]
    jefatura.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": jefatura.email, "password": "clave12345"})

    r = api.get("/panel/tareas")
    assert r.status_code == 200
    assert "CT-TAREA-WEB" in r.text
