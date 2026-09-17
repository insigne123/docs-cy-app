"""API de licitaciones: Fase I, adjudicación y Fase II del contrato resultante."""
from __future__ import annotations

from app.enums import Rol


def test_licitacion_flujo_completo_por_api(api, usuarios, unidad):
    u = usuarios
    lid = api.post(
        "/licitaciones",
        json={
            "codigo": "LIC-API-1",
            "objeto": "Mantención de flota",
            "unidad_solicitante_id": unidad.id,
            "solicitante_id": u[Rol.admin_licitaciones].id,
            "moneda": "CLP",
        },
    ).json()["id"]

    def tl(hacia, uid, **kw):
        return api.post(f"/licitaciones/{lid}/transiciones", json={"hacia": hacia, "usuario_id": uid, **kw})

    assert tl("examen_admisibilidad", u[Rol.admin_licitaciones].id).status_code == 200
    assert tl("revision_bases", u[Rol.legal].id).status_code == 200
    assert tl("preparacion_oferta", u[Rol.legal].id, extra={"informe_riesgos_ok": True}).status_code == 200
    assert tl(
        "presentacion_oferta",
        u[Rol.tecnica].id,
        extra={"oferta_tecnica_ok": True, "oferta_economica_ok": True},
    ).status_code == 200
    assert tl("evaluacion_resultado", u[Rol.admin_licitaciones].id).status_code == 200

    r = api.post(
        f"/licitaciones/{lid}/adjudicar",
        json={"usuario_id": u[Rol.admin_licitaciones].id, "codigo_contrato": "CT-ADJ-1"},
    )
    assert r.status_code == 201, r.text
    contrato = r.json()
    assert contrato["linea"] == "C_licitacion"
    assert contrato["estado"] == "formalizacion_ajuste"
    cid = contrato["id"]

    lf = api.get(f"/licitaciones/{lid}").json()
    assert lf["licitacion"]["estado"] == "adjudicada"
    assert lf["licitacion"]["contrato_id"] == cid

    def tc(hacia, uid, **kw):
        return api.post(f"/contratos/{cid}/transiciones", json={"hacia": hacia, "usuario_id": uid, **kw})

    assert tc("constitucion_garantias", u[Rol.legal].id, extra={"coherente_con_oferta": True}).status_code == 200
    assert tc("firma", u[Rol.financiera].id).status_code == 422  # sin garantía

    api.post(
        f"/contratos/{cid}/garantias",
        json={
            "tipo": "fiel_cumplimiento",
            "instrumento": "boleta_bancaria",
            "monto": 1_000_000,
            "moneda": "CLP",
            "fecha_emision": "2026-01-01",
            "fecha_vencimiento": "2027-06-01",
            "estado": "vigente",
        },
    )
    assert tc("firma", u[Rol.financiera].id).status_code == 200
    assert tc("integracion", u[Rol.legal].id, extra={"documento_firmado": True}).status_code == 200
    api.patch(f"/contratos/{cid}", json={"administrador_id": u[Rol.admin_contratos].id, "fecha_fin_vigencia": "2030-01-01"})
    r = tc("vigente", u[Rol.admin_contratos].id)
    assert r.status_code == 200
    assert r.json()["contrato"]["estado"] == "vigente"


def test_licitacion_no_adjudicada_exige_analisis(api, usuarios, unidad):
    u = usuarios
    lid = api.post(
        "/licitaciones",
        json={
            "codigo": "LIC-API-2",
            "objeto": "Suministro",
            "unidad_solicitante_id": unidad.id,
            "solicitante_id": u[Rol.admin_licitaciones].id,
        },
    ).json()["id"]

    def tl(hacia, uid, **kw):
        return api.post(f"/licitaciones/{lid}/transiciones", json={"hacia": hacia, "usuario_id": uid, **kw})

    tl("examen_admisibilidad", u[Rol.admin_licitaciones].id)
    tl("revision_bases", u[Rol.legal].id)
    tl("preparacion_oferta", u[Rol.legal].id, extra={"informe_riesgos_ok": True})
    tl("presentacion_oferta", u[Rol.tecnica].id, extra={"oferta_tecnica_ok": True, "oferta_economica_ok": True})
    tl("evaluacion_resultado", u[Rol.admin_licitaciones].id)

    assert tl("no_adjudicada", u[Rol.admin_licitaciones].id).status_code == 422
    r = tl("no_adjudicada", u[Rol.admin_licitaciones].id, extra={"analisis_interno": "precio fuera de mercado"})
    assert r.status_code == 200
    assert r.json()["licitacion"]["resultado"] == "no_adjudicado"
