"""Módulo web de licitaciones (Flujo Completo): creación, avance y adjudicación."""
from __future__ import annotations

from app.enums import Rol
from app.services.auth import hash_password


def _login(api, session, usuarios, rol, password="clave12345"):
    u = usuarios[rol]
    u.password_hash = hash_password(password)
    session.commit()
    api.post("/login", data={"email": u.email, "password": password})
    return u


def test_nueva_licitacion_requiere_login(api):
    r = api.get("/panel/licitaciones/nuevo", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login")


def test_crear_licitacion_y_avanzar_hasta_adjudicar(api, session, usuarios, unidad):
    _login(api, session, usuarios, Rol.admin_licitaciones)
    r = api.post(
        "/panel/licitaciones/nuevo",
        data={"objeto": "Mantención de flota", "unidad_solicitante_id": str(unidad.id), "moneda": "CLP"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    ficha_url = r.headers["location"].split("?")[0]
    assert "/panel/licitaciones/" in ficha_url

    detalle = api.get(ficha_url)
    assert detalle.status_code == 200
    assert "Mantención de flota" in detalle.text
    assert "Flujo Completo" in detalle.text

    def transicion(hacia, actor, **extra):
        _login(api, session, usuarios, actor)
        return api.post(f"{ficha_url}/transicion", data={"hacia": hacia, **extra}, follow_redirects=False)

    assert transicion("examen_admisibilidad", Rol.admin_licitaciones).status_code == 303
    assert transicion("revision_bases", Rol.legal).status_code == 303
    r = transicion("preparacion_oferta", Rol.legal, informe_riesgos_ok="1")
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    r = transicion("presentacion_oferta", Rol.tecnica, oferta_tecnica_ok="1", oferta_economica_ok="1")
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    assert transicion("evaluacion_resultado", Rol.admin_licitaciones).status_code == 303

    _login(api, session, usuarios, Rol.admin_licitaciones)
    r = api.post(f"{ficha_url}/adjudicar", data={"codigo_contrato": "CT-LIC-TEST"}, follow_redirects=False)
    assert r.status_code == 303
    assert "ok=" in r.headers["location"]
    contrato_url = r.headers["location"].split("?")[0]
    ficha_contrato = api.get(contrato_url)
    assert ficha_contrato.status_code == 200
    assert "Flujo Completo" in ficha_contrato.text
    assert "formalizacion_ajuste" in ficha_contrato.text
