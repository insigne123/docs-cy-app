"""Subida y previsualización del archivo real de un documento (contrato o
licitación) — antes 'ruta' era solo texto, sin ningún archivo detrás."""
from __future__ import annotations

from app.enums import LineaContrato, Rol
from app.services.auth import hash_password
from app.services.contratos import crear_contrato
from app.services.licitaciones import crear_licitacion


def test_subir_y_previsualizar_documento_contrato(api, session, usuarios, unidad, contraparte):
    c = crear_contrato(
        session, codigo="CT-DOC-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    legal = usuarios[Rol.legal]
    legal.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": legal.email, "password": "clave12345"})

    r = api.post(
        f"/panel/contratos/{c.id}/documentos",
        data={"tipo": "borrador"},
        files={"archivo": ("borrador.txt", b"contenido del borrador", "text/plain")},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    r = api.get(f"/panel/contratos/{c.id}")
    assert r.status_code == 200
    assert "borrador.txt" in r.text
    assert "Previsualizar" in r.text

    from app.models.contrato import Documento
    from sqlalchemy import select
    documento = session.scalars(select(Documento).where(Documento.entidad_id == c.id)).first()
    assert documento.contenido == b"contenido del borrador"
    assert documento.version == 1

    r = api.get(f"/panel/contratos/{c.id}/documentos/{documento.id}/archivo")
    assert r.status_code == 200
    assert r.content == b"contenido del borrador"
    assert "inline" in r.headers["content-disposition"]

    # Segunda subida del mismo tipo incrementa la version.
    api.post(
        f"/panel/contratos/{c.id}/documentos",
        data={"tipo": "borrador"},
        files={"archivo": ("borrador_v2.txt", b"version 2", "text/plain")},
    )
    v2 = session.scalars(
        select(Documento).where(Documento.entidad_id == c.id, Documento.nombre_archivo == "borrador_v2.txt")
    ).first()
    assert v2.version == 2


def test_documento_de_otro_contrato_no_se_puede_previsualizar(api, session, usuarios, unidad, contraparte):
    c1 = crear_contrato(
        session, codigo="CT-DOC-A", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    c2 = crear_contrato(
        session, codigo="CT-DOC-B", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    legal = usuarios[Rol.legal]
    legal.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": legal.email, "password": "clave12345"})

    api.post(
        f"/panel/contratos/{c1.id}/documentos", data={"tipo": "borrador"},
        files={"archivo": ("b.txt", b"x", "text/plain")},
    )
    from app.models.contrato import Documento
    from sqlalchemy import select
    documento = session.scalars(select(Documento).where(Documento.entidad_id == c1.id)).first()

    r = api.get(f"/panel/contratos/{c2.id}/documentos/{documento.id}/archivo")
    assert r.status_code == 404


def test_subir_documento_licitacion(api, session, usuarios, unidad, contraparte):
    lic = crear_licitacion(
        session, codigo="LIC-DOC-1", objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    tecnica = usuarios[Rol.tecnica]
    tecnica.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": tecnica.email, "password": "clave12345"})

    r = api.post(
        f"/panel/licitaciones/{lic.id}/documentos",
        data={"tipo": "oferta_tecnica"},
        files={"archivo": ("oferta.pdf", b"%PDF-contenido", "application/pdf")},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    r = api.get(f"/panel/licitaciones/{lic.id}")
    assert "oferta.pdf" in r.text
