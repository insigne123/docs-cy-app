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


def test_crear_usuario_con_password(api):
    r = api.post(
        "/usuarios",
        json={"nombre": "Ana", "email": "ana@empresa.cl", "rol": "legal", "password": "hola12345"},
    )
    assert r.status_code == 201
    tok = api.post("/auth/login", json={"email": "ana@empresa.cl", "password": "hola12345"}).json()
    assert "token" in tok


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
