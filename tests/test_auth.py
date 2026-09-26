"""Autenticación mínima: hash de contraseñas, tokens y protección de endpoints."""
from __future__ import annotations

from app.enums import Rol
from app.services.auth import crear_token, hash_password, leer_token, verify_password


def test_hash_password_roundtrip():
    h = hash_password("clave-secreta")
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password("clave-secreta", h)
    assert not verify_password("otra", h)
    assert not verify_password("x", None)


def test_token_roundtrip():
    assert leer_token(crear_token(42)) == 42
    assert leer_token("basura.basura") is None
    assert leer_token("sinpunto") is None


def test_login_y_proteccion(api, session, usuarios, unidad, contraparte, monkeypatch):
    from app.config import settings

    u = usuarios[Rol.unidad_solicitante]
    u.password_hash = hash_password("secreta123")
    session.commit()

    body = {
        "codigo": "CT-AUTH", "linea": "A_regular", "objeto": "x",
        "unidad_solicitante_id": unidad.id, "solicitante_id": u.id, "contraparte_id": contraparte.id,
    }

    # sin auth: pasa igual que siempre
    assert api.post("/contratos", json={**body, "codigo": "CT-NOAUTH"}).status_code == 201

    monkeypatch.setattr(settings, "auth_required", True)
    assert api.post("/contratos", json=body).status_code == 401
    assert api.post("/auth/login", json={"email": u.email, "password": "mala"}).status_code == 401

    tok = api.post("/auth/login", json={"email": u.email, "password": "secreta123"}).json()["token"]
    cab = {"Authorization": f"Bearer {tok}"}
    assert api.post("/contratos", json=body, headers=cab).status_code == 201
    assert api.get("/auth/yo", headers=cab).json()["email"] == u.email
    assert api.get("/auth/yo").status_code == 401

    # catálogos, alertas y métricas también quedan protegidos (antes no lo estaban)
    assert api.get("/usuarios").status_code == 401
    assert api.get("/usuarios", headers=cab).status_code == 200
    assert api.get("/alertas").status_code == 401
    assert api.get("/metricas").status_code == 401
    r = api.get("/panel.json", follow_redirects=False)
    assert r.status_code == 401 and r.json()["detail"] == "Autenticación requerida"


def test_catalogos_api_exigen_admin_sistema_con_auth(api, usuarios, monkeypatch):
    """La API de catálogos no tenía ningún chequeo de rol propio: cualquier
    usuario autenticado (de cualquier rol) podía llamarla directo y saltarse
    la restricción a admin_sistema que sí aplica el panel web — p. ej.
    crearse a sí mismo una cuenta con más privilegios."""
    from app.config import settings
    from app.services.auth import hash_password

    legal = usuarios[Rol.legal]
    legal.password_hash = hash_password("clave-legal-1")
    admin = usuarios[Rol.admin_sistema]
    admin.password_hash = hash_password("clave-admin-1")

    monkeypatch.setattr(settings, "auth_required", True)
    tok_legal = api.post("/auth/login", json={"email": legal.email, "password": "clave-legal-1"}).json()["token"]
    tok_admin = api.post("/auth/login", json={"email": admin.email, "password": "clave-admin-1"}).json()["token"]

    cuerpo_unidad = {"nombre": "Unidad API Test", "tipo": "interna"}
    r = api.post("/unidades", json=cuerpo_unidad, headers={"Authorization": f"Bearer {tok_legal}"})
    assert r.status_code == 403
    r = api.post("/unidades", json=cuerpo_unidad, headers={"Authorization": f"Bearer {tok_admin}"})
    assert r.status_code == 201

    cuerpo_usuario = {"nombre": "Otro", "email": "otro-api@empresa.cl", "rol": "admin_sistema"}
    assert api.post("/usuarios", json=cuerpo_usuario, headers={"Authorization": f"Bearer {tok_legal}"}).status_code == 403


def test_transicion_api_usa_identidad_de_sesion_no_del_payload(api, session, usuarios, unidad, contraparte, monkeypatch):
    """Antes, /contratos/{id}/transiciones tomaba usuario_id (y hasta el rol)
    directo del cuerpo JSON: cualquiera autenticado podia indicar el id de
    otro usuario -o directamente el rol que quisiera- y actuar en su nombre.
    Con auth obligatoria, el actor real siempre debe salir de la sesión."""
    from app.config import settings
    from app.services.auth import hash_password

    solicitante = usuarios[Rol.unidad_solicitante]
    solicitante.password_hash = hash_password("clave-sol-1")
    legal = usuarios[Rol.legal]
    session.commit()

    r = api.post("/contratos", json={
        "codigo": "CT-IMPERSONAR", "linea": "A_regular", "objeto": "x",
        "unidad_solicitante_id": unidad.id, "solicitante_id": solicitante.id,
        "contraparte_id": contraparte.id,
    })
    assert r.status_code == 201
    cid = r.json()["id"]

    monkeypatch.setattr(settings, "auth_required", True)
    tok = api.post("/auth/login", json={"email": solicitante.email, "password": "clave-sol-1"}).json()["token"]
    cab = {"Authorization": f"Bearer {tok}"}

    # Unidad Solicitante sí puede avanzar ingreso -> aprobacion_jefatura (A2)...
    r = api.post(
        f"/contratos/{cid}/transiciones",
        json={"hacia": "aprobacion_jefatura", "usuario_id": legal.id, "rol": "legal"},
        headers=cab,
    )
    assert r.status_code == 200

    # ...pero aprobacion_jefatura -> admisibilidad_1 (A5) es exclusiva de
    # Jefatura. El payload dice usuario_id=legal.id y rol=legal (que sí
    # podría ejecutarla), y aun así debe fallar con 403: la sesión real
    # sigue siendo Unidad Solicitante, y eso es lo único que debe importar.
    r = api.post(
        f"/contratos/{cid}/transiciones",
        json={"hacia": "admisibilidad_1", "usuario_id": legal.id, "rol": "legal"},
        headers=cab,
    )
    assert r.status_code == 403


def test_login_se_bloquea_tras_intentos_fallidos(api, session, usuarios):
    from app.services.auth import MAX_INTENTOS_LOGIN, hash_password

    u = usuarios[Rol.unidad_solicitante]
    u.password_hash = hash_password("clave-correcta")
    session.commit()

    for _ in range(MAX_INTENTOS_LOGIN):
        r = api.post("/login", data={"email": u.email, "password": "mala"}, follow_redirects=False)
        assert r.status_code == 303 and "error=1" in r.headers["location"]

    # Ya alcanzó el máximo: aunque ahora mande la clave correcta, queda bloqueado.
    r = api.post("/login", data={"email": u.email, "password": "clave-correcta"}, follow_redirects=False)
    assert r.status_code == 303 and "error=bloqueado" in r.headers["location"]

    session.refresh(u)
    assert u.bloqueado_hasta is not None

    # Se levanta manualmente (o expiraría solo): un login correcto lo resetea.
    u.bloqueado_hasta = None
    session.commit()
    r = api.post("/login", data={"email": u.email, "password": "clave-correcta"}, follow_redirects=False)
    assert r.status_code == 303 and "error" not in r.headers["location"]
    session.refresh(u)
    assert u.intentos_fallidos == 0


def test_login_api_se_bloquea_tras_intentos_fallidos(api, session, usuarios):
    from app.services.auth import MAX_INTENTOS_LOGIN, hash_password

    u = usuarios[Rol.legal]
    u.password_hash = hash_password("clave-correcta")
    session.commit()

    for _ in range(MAX_INTENTOS_LOGIN):
        assert api.post("/auth/login", json={"email": u.email, "password": "mala"}).status_code == 401

    r = api.post("/auth/login", json={"email": u.email, "password": "clave-correcta"})
    assert r.status_code == 429


def test_subrecursos_api_exigen_rol_correcto(api, session, usuarios, unidad, contraparte, monkeypatch):
    """Los sub-recursos de contrato (garantías, hitos, multas) no pasan por el
    motor de estados, asi que resolver_actor_transicion no los cubre: sin un
    chequeo propio, cualquier usuario autenticado podia agregarlos aunque el
    panel web se lo reserve a un rol especifico (Financiera para garantias,
    por ejemplo)."""
    from app.config import settings
    from app.services.auth import hash_password

    r = api.post("/contratos", json={
        "codigo": "CT-SUBREC", "linea": "A_regular", "objeto": "x",
        "unidad_solicitante_id": unidad.id, "solicitante_id": usuarios[Rol.unidad_solicitante].id,
        "contraparte_id": contraparte.id,
    })
    cid = r.json()["id"]

    solicitante = usuarios[Rol.unidad_solicitante]
    solicitante.password_hash = hash_password("clave-sol-1")
    financiera = usuarios[Rol.financiera]
    financiera.password_hash = hash_password("clave-fin-1")
    session.commit()

    monkeypatch.setattr(settings, "auth_required", True)
    tok_sol = api.post("/auth/login", json={"email": solicitante.email, "password": "clave-sol-1"}).json()["token"]
    tok_fin = api.post("/auth/login", json={"email": financiera.email, "password": "clave-fin-1"}).json()["token"]

    cuerpo_garantia = {
        "tipo": "fiel_cumplimiento", "instrumento": "boleta_bancaria", "monto": 100,
        "moneda": "CLP", "fecha_emision": "2026-01-01", "fecha_vencimiento": "2027-01-01",
    }
    r = api.post(f"/contratos/{cid}/garantias", json=cuerpo_garantia, headers={"Authorization": f"Bearer {tok_sol}"})
    assert r.status_code == 403
    r = api.post(f"/contratos/{cid}/garantias", json=cuerpo_garantia, headers={"Authorization": f"Bearer {tok_fin}"})
    assert r.status_code == 201


def test_crear_usuario_con_password(api):
    r = api.post(
        "/usuarios",
        json={"nombre": "Ana", "email": "ana@empresa.cl", "rol": "legal", "password": "hola12345"},
    )
    assert r.status_code == 201
    tok = api.post("/auth/login", json={"email": "ana@empresa.cl", "password": "hola12345"}).json()
    assert "token" in tok


def test_password_minima_al_crear_usuario(api, usuarios, session):
    from app.models.core import Usuario
    from app.services.auth import hash_password
    from sqlalchemy import select

    r = api.post(
        "/usuarios",
        json={"nombre": "Corta", "email": "corta@empresa.cl", "rol": "legal", "password": "1234567"},
    )
    assert r.status_code == 422

    admin = usuarios[Rol.admin_sistema]
    admin.password_hash = hash_password("clave-admin-2")
    session.commit()
    api.post("/login", data={"email": admin.email, "password": "clave-admin-2"})

    r = api.post("/panel/catalogos/usuarios", data={
        "nombre": "Corta Web", "email": "cortaweb@empresa.cl", "rol": "legal", "password": "1234567",
    }, follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]
    assert session.scalars(select(Usuario).where(Usuario.email == "cortaweb@empresa.cl")).first() is None


def test_login_web_cookie_y_email_normalizado(session):
    """Flujo web real: POST /login fija __session y el panel la acepta (vía https)."""
    from fastapi.testclient import TestClient

    from app.api.app import create_app
    from app.api.deps import get_db
    from app.models.core import Usuario

    session.add(Usuario(
        nombre="Admin", email="admin@empresa.cl", rol=Rol.admin_sistema,
        activo=True, password_hash=hash_password("Secreta123"),
    ))
    session.commit()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app, base_url="https://testserver", follow_redirects=False) as web:
            r = web.post("/login", data={"email": "  ADMIN@empresa.cl ", "password": "Secreta123"})
            assert r.status_code == 303 and r.headers["location"] == "/panel"
            assert "__session" in r.cookies
            r2 = web.get("/panel")
            assert r2.status_code == 200
            assert "Panel de Contratos y Licitaciones" in r2.text
    finally:
        app.dependency_overrides.clear()
