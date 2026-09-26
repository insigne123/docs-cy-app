"""Búsqueda global: contratos y licitaciones por código, objeto o contraparte."""
from __future__ import annotations

from app.enums import LineaContrato, Rol
from app.services.auth import hash_password
from app.services.busqueda import buscar_global
from app.services.contratos import crear_contrato
from app.services.licitaciones import crear_licitacion


def test_buscar_global_sin_texto_no_devuelve_nada(session):
    assert buscar_global(session, "") == {"q": "", "contratos": [], "licitaciones": []}


def test_buscar_global_por_codigo_objeto_y_contraparte(session, usuarios, unidad, contraparte):
    crear_contrato(
        session, codigo="CT-BUSCA-1", linea=LineaContrato.A_regular, objeto="Servicio de aseo",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    crear_licitacion(
        session, codigo="LIC-BUSCA-1", objeto="Licitación de mantención",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()

    r = buscar_global(session, "CT-BUSCA")
    assert [c["codigo"] for c in r["contratos"]] == ["CT-BUSCA-1"]

    r = buscar_global(session, "aseo")
    assert [c["codigo"] for c in r["contratos"]] == ["CT-BUSCA-1"]

    r = buscar_global(session, contraparte.razon_social[:6])
    assert [c["codigo"] for c in r["contratos"]] == ["CT-BUSCA-1"]

    r = buscar_global(session, "mantención")
    assert [l["codigo"] for l in r["licitaciones"]] == ["LIC-BUSCA-1"]

    assert buscar_global(session, "no-existe-esto")["contratos"] == []


def test_pagina_buscar_requiere_login_y_bloquea_unidad_solicitante(api, session, usuarios, unidad, contraparte):
    crear_contrato(
        session, codigo="CT-BUSCA-WEB", linea=LineaContrato.A_regular, objeto="Objeto buscable",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()

    solicitante = usuarios[Rol.unidad_solicitante]
    solicitante.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": solicitante.email, "password": "clave12345"})
    r = api.get("/panel/buscar?q=CT-BUSCA-WEB", follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]

    admin = usuarios[Rol.admin_contratos]
    admin.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": admin.email, "password": "clave12345"})
    r = api.get("/panel/buscar?q=CT-BUSCA-WEB")
    assert r.status_code == 200
    assert "CT-BUSCA-WEB" in r.text


def test_pagina_buscar_exige_login_con_auth_obligatoria(api, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "auth_required", True)
    r = api.get("/panel/buscar?q=algo", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")
