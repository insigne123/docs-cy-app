"""API de contratos: creación, ficha, transiciones y sub-recursos."""
from __future__ import annotations

from app.enums import Rol


def _crear(api, usuarios, unidad, contraparte, **over):
    body = {
        "codigo": over.pop("codigo", "CT-API-1"),
        "linea": "A_regular",
        "objeto": "Servicio de prueba",
        "unidad_solicitante_id": unidad.id,
        "solicitante_id": usuarios[Rol.unidad_solicitante].id,
        "contraparte_id": contraparte.id,
        "monto": 1_000_000,
        "moneda": "CLP",
    }
    body.update(over)
    r = api.post("/contratos", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _trans(api, cid, hacia, uid, **kw):
    return api.post(f"/contratos/{cid}/transiciones", json={"hacia": hacia, "usuario_id": uid, **kw})


def test_health(api):
    assert api.get("/health").json()["status"] == "ok"


def test_crear_y_ficha(api, usuarios, unidad, contraparte):
    cid = _crear(api, usuarios, unidad, contraparte)
    f = api.get(f"/contratos/{cid}")
    assert f.status_code == 200
    cuerpo = f.json()
    assert cuerpo["contrato"]["estado"] == "ingreso"
    assert cuerpo["contrato"]["codigo"] == "CT-API-1"
    assert len(cuerpo["historial"]) == 1
    assert cuerpo["historial"][0]["estado_destino"] == "ingreso"


def test_flujo_a_completo_por_api(api, usuarios, unidad, contraparte):
    u = usuarios
    cid = _crear(api, usuarios, unidad, contraparte)
    assert _trans(api, cid, "aprobacion_jefatura", u[Rol.unidad_solicitante].id).status_code == 200
    assert _trans(api, cid, "admisibilidad_1", u[Rol.jefatura].id).status_code == 200
    assert _trans(api, cid, "admisibilidad_2", u[Rol.legal].id).status_code == 200
    assert api.patch(f"/contratos/{cid}", json={"abogado_id": u[Rol.legal].id}).status_code == 200
    assert _trans(api, cid, "elaboracion", u[Rol.legal].id).status_code == 200
    assert _trans(api, cid, "visacion", u[Rol.legal].id, extra={"borrador_cargado": True}).status_code == 200
    assert _trans(api, cid, "firma", u[Rol.legal].id).status_code == 200
    assert _trans(api, cid, "integracion", u[Rol.legal].id, extra={"documento_firmado": True}).status_code == 200
    assert api.patch(
        f"/contratos/{cid}",
        json={"administrador_id": u[Rol.admin_contratos].id, "fecha_fin_vigencia": "2030-01-01"},
    ).status_code == 200
    r = _trans(api, cid, "vigente", u[Rol.admin_contratos].id)
    assert r.status_code == 200
    ficha = r.json()
    assert ficha["contrato"]["estado"] == "vigente"
    assert len(ficha["historial"]) == 9
    assert ficha["historial"][-1]["estado_destino"] == "vigente"


def test_rol_incorrecto_403(api, usuarios, unidad, contraparte):
    u = usuarios
    cid = _crear(api, usuarios, unidad, contraparte)
    _trans(api, cid, "aprobacion_jefatura", u[Rol.unidad_solicitante].id)
    _trans(api, cid, "admisibilidad_1", u[Rol.jefatura].id)
    r = _trans(api, cid, "admisibilidad_2", u[Rol.jefatura].id)
    assert r.status_code == 403


def test_transicion_no_permitida_409(api, usuarios, unidad, contraparte):
    cid = _crear(api, usuarios, unidad, contraparte)
    r = _trans(api, cid, "firma", usuarios[Rol.legal].id)
    assert r.status_code == 409


def test_precondicion_422(api, usuarios, unidad, contraparte):
    u = usuarios
    cid = _crear(api, usuarios, unidad, contraparte)
    _trans(api, cid, "aprobacion_jefatura", u[Rol.unidad_solicitante].id)
    _trans(api, cid, "admisibilidad_1", u[Rol.jefatura].id)
    _trans(api, cid, "admisibilidad_2", u[Rol.legal].id)
    r = _trans(api, cid, "elaboracion", u[Rol.legal].id)  # sin abogado asignado
    assert r.status_code == 422


def test_firma_requiere_garantia_por_api(api, usuarios, unidad, contraparte):
    u = usuarios
    cid = _crear(api, usuarios, unidad, contraparte, codigo="CT-API-GAR", requiere_garantia=True)
    _trans(api, cid, "aprobacion_jefatura", u[Rol.unidad_solicitante].id)
    _trans(api, cid, "admisibilidad_1", u[Rol.jefatura].id)
    _trans(api, cid, "admisibilidad_2", u[Rol.legal].id)
    api.patch(f"/contratos/{cid}", json={"abogado_id": u[Rol.legal].id})
    _trans(api, cid, "elaboracion", u[Rol.legal].id)
    _trans(api, cid, "visacion", u[Rol.legal].id, extra={"borrador_cargado": True})

    assert _trans(api, cid, "firma", u[Rol.legal].id).status_code == 422

    g = api.post(
        f"/contratos/{cid}/garantias",
        json={
            "tipo": "fiel_cumplimiento",
            "instrumento": "boleta_bancaria",
            "monto": 100000,
            "moneda": "CLP",
            "fecha_emision": "2026-01-01",
            "fecha_vencimiento": "2027-01-01",
            "estado": "vigente",
        },
    )
    assert g.status_code == 201
    assert _trans(api, cid, "firma", u[Rol.legal].id).status_code == 200


def test_listar_con_filtros(api, usuarios, unidad, contraparte):
    _crear(api, usuarios, unidad, contraparte, codigo="CT-F1")
    _crear(api, usuarios, unidad, contraparte, codigo="CT-F2")
    r = api.get("/contratos", params={"linea": "A_regular", "estado": "ingreso"})
    assert r.status_code == 200
    assert {c["codigo"] for c in r.json()} == {"CT-F1", "CT-F2"}
    assert api.get("/contratos", params={"estado": "vigente"}).json() == []


def test_crear_linea_b_sin_formato_400(api, usuarios, unidad, contraparte):
    r = api.post(
        "/contratos",
        json={
            "codigo": "CT-B-ERR",
            "linea": "B_autogestionado",
            "objeto": "sin formato",
            "unidad_solicitante_id": unidad.id,
            "solicitante_id": usuarios[Rol.unidad_solicitante].id,
        },
    )
    assert r.status_code == 400
