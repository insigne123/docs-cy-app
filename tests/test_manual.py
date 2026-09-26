"""Manual de uso: accesible sin login, con el botón visible en toda la app."""
from __future__ import annotations


def test_manual_accesible_sin_login(api):
    r = api.get("/manual")
    assert r.status_code == 200
    assert "Manual de uso" in r.text
    assert "Mis tareas" in r.text
    assert "Flujo Autogestionado" in r.text


def test_boton_manual_visible_en_login(api):
    r = api.get("/login")
    assert r.status_code == 200
    assert 'href="/manual"' in r.text
