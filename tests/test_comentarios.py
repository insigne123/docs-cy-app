"""Comentarios libres en la ficha de un contrato o licitación."""
from __future__ import annotations

from app.enums import LineaContrato, Rol
from app.services.auth import hash_password
from app.services.comentarios import agregar_comentario, listar_comentarios
from app.services.contratos import crear_contrato
from app.services.licitaciones import crear_licitacion


def test_agregar_y_listar_comentarios(session, usuarios, unidad, contraparte):
    c = crear_contrato(
        session, codigo="CT-COM-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    agregar_comentario(session, "contrato", c.id, usuarios[Rol.legal].id, "  Ojo con el plazo  ")
    session.commit()

    comentarios = listar_comentarios(session, "contrato", c.id)
    assert len(comentarios) == 1
    assert comentarios[0]["texto"] == "Ojo con el plazo"
    assert comentarios[0]["usuario"] == usuarios[Rol.legal].nombre


def test_comentar_contrato_desde_la_ficha(api, session, usuarios, unidad, contraparte):
    c = crear_contrato(
        session, codigo="CT-COM-WEB", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    legal = usuarios[Rol.legal]
    legal.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": legal.email, "password": "clave12345"})

    r = api.post(f"/panel/contratos/{c.id}/comentarios", data={"texto": "Falta el anexo firmado"}, follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    r = api.get(f"/panel/contratos/{c.id}")
    assert "Falta el anexo firmado" in r.text
    assert legal.nombre in r.text

    r = api.post(f"/panel/contratos/{c.id}/comentarios", data={"texto": "   "}, follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]


def test_comentar_licitacion_desde_la_ficha(api, session, usuarios, unidad, contraparte):
    lic = crear_licitacion(
        session, codigo="LIC-COM-WEB", objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    tecnica = usuarios[Rol.tecnica]
    tecnica.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": tecnica.email, "password": "clave12345"})

    r = api.post(f"/panel/licitaciones/{lic.id}/comentarios", data={"texto": "Revisar bases técnicas"}, follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    r = api.get(f"/panel/licitaciones/{lic.id}")
    assert "Revisar bases técnicas" in r.text
