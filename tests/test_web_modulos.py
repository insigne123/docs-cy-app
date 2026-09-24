"""Módulos web de operación: nueva solicitud, edición, garantías y avance de flujo."""
from __future__ import annotations

from app.enums import Rol
from app.services.auth import hash_password


def _login(api, session, usuarios, rol=Rol.unidad_solicitante, password="clave12345"):
    u = usuarios[rol]
    u.password_hash = hash_password(password)
    session.commit()
    r = api.post("/login", data={"email": u.email, "password": password})
    assert r.status_code in (303, 200)
    return u


def test_nuevo_contrato_requiere_login(api):
    r = api.get("/panel/contratos/nuevo", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login")


def test_crear_contrato_flujo_regular(api, session, usuarios, unidad, contraparte):
    _login(api, session, usuarios)
    r = api.post(
        "/panel/contratos/nuevo",
        data={
            "linea": "A_regular",
            "objeto": "Servicio de prueba",
            "unidad_solicitante_id": str(unidad.id),
            "contraparte_id": str(contraparte.id),
            "monto": "1000000",
            "moneda": "CLP",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/panel/contratos/" in r.headers["location"]
    detalle = api.get(r.headers["location"])
    assert detalle.status_code == 200
    assert "Servicio de prueba" in detalle.text
    assert "Flujo Regular" in detalle.text


def test_crear_autogestionado_sin_formato_muestra_error(api, session, usuarios, unidad, contraparte):
    _login(api, session, usuarios)
    r = api.post(
        "/panel/contratos/nuevo",
        data={
            "linea": "B_autogestionado",
            "objeto": "NDA",
            "unidad_solicitante_id": str(unidad.id),
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "error=" in r.headers["location"]


def test_editar_contrato(api, session, usuarios, unidad, contraparte):
    u = _login(api, session, usuarios, rol=Rol.admin_contratos)
    from app.enums import LineaContrato, Moneda
    from app.services.contratos import crear_contrato

    c = crear_contrato(
        session, codigo="CT-WEB-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=u, contraparte=contraparte,
    )
    session.commit()

    r = api.post(
        f"/panel/contratos/{c.id}/editar",
        data={
            "administrador_id": str(u.id),
            "monto": "500000",
            "moneda": "CLP",
            "vigencia_indefinida": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    session.refresh(c)
    assert c.administrador_id == u.id
    assert c.vigencia_indefinida is True


def test_agregar_garantia_y_transicion(api, session, usuarios, unidad, contraparte):
    u = _login(api, session, usuarios, rol=Rol.legal)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato
    from tests._helpers import avanzar_a
    from app.enums import EstadoContrato
    from app.state_machine import MotorEstados

    c = crear_contrato(
        session, codigo="CT-WEB-2", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante],
        contraparte=contraparte, requiere_garantia=True,
    )
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.visacion)
    session.commit()

    # Firma sin garantía -> error visible, no un 500
    r = api.post(f"/panel/contratos/{c.id}/transicion", data={"hacia": "firma"}, follow_redirects=False)
    assert r.status_code == 303
    assert "error=" in r.headers["location"]

    r = api.post(
        f"/panel/contratos/{c.id}/garantias",
        data={
            "tipo": "fiel_cumplimiento", "instrumento": "boleta_bancaria",
            "monto": "100000", "moneda": "CLP",
            "fecha_emision": "2026-01-01", "fecha_vencimiento": "2027-01-01",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    r = api.post(f"/panel/contratos/{c.id}/transicion", data={"hacia": "firma"}, follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(c)
    assert c.estado.value == "firma"


def test_transicion_a_aclaraciones_desde_ingreso(api, session, usuarios, unidad, contraparte):
    """Regresión: elegir 'aclaraciones' como destino debe funcionar sin un checkbox
    aparte de 'completitud' (se deriva del estado elegido, ver routes.py)."""
    u = _login(api, session, usuarios, rol=Rol.legal)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato

    c = crear_contrato(
        session, codigo="CT-WEB-3", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()

    r = api.post(f"/panel/contratos/{c.id}/transicion", data={"hacia": "aclaraciones"}, follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(c)
    assert c.estado.value == "aclaraciones"
    assert c.retorno_a == "ingreso"
