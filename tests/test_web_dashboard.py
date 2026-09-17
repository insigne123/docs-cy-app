"""Panel web: agrupación por mes, filtros, semáforo de vigencia y ficha de detalle."""
from __future__ import annotations

from datetime import date, timedelta

HOY = date.today()


def _tarjetas(datos):
    return {c["codigo"]: c for g in datos["grupos"] for c in g["contratos"]}


def test_indicadores_y_semaforo(api, cartera):
    d = api.get("/panel.json", params={"agrupacion": "vencimiento"}).json()
    ind = d["indicadores"]
    assert ind["total"] == 5
    assert ind["vigentes"] == 1
    assert ind["vencidos"] == 1
    assert ind["por_vencer"] == 2          # C-PORVENCER + C-RENOV
    assert ind["en_renovacion"] == 1
    assert ind["monto_total"]["CLP"] == "4000000.00"

    t = _tarjetas(d)
    assert t["C-VIG"]["semaforo"] == "vigente"
    assert t["C-VENCIDO"]["semaforo"] == "vencido"
    assert t["C-PORVENCER"]["semaforo"] == "por_vencer"
    assert t["C-PORVENCER"]["nivel_alerta"] == "urgente"
    assert t["C-RENOV"]["semaforo"] == "en_renovacion"
    assert t["C-TRAMITE"]["semaforo"] == "en_tramite"


def test_agrupacion_por_vencimiento(api, cartera):
    d = api.get("/panel.json", params={"agrupacion": "vencimiento"}).json()
    periodos = [g["periodo"] for g in d["grupos"]]
    assert periodos == sorted(p for p in periodos if p != "sin_fecha") + ["sin_fecha"]
    assert periodos[-1] == "sin_fecha"
    sin_fecha = next(g for g in d["grupos"] if g["periodo"] == "sin_fecha")
    assert [c["codigo"] for c in sin_fecha["contratos"]] == ["C-TRAMITE"]


def test_agrupacion_por_ingreso(api, cartera):
    d = api.get("/panel.json", params={"agrupacion": "ingreso"}).json()
    periodos = {g["periodo"] for g in d["grupos"]}
    assert "2026-01" in periodos and "2026-02" in periodos
    assert all(g["periodo"] != "sin_fecha" for g in d["grupos"])  # todos tienen fecha_ingreso


def test_filtros(api, cartera):
    assert api.get("/panel.json", params={"linea": "B_autogestionado"}).json()["indicadores"]["total"] == 0
    assert api.get("/panel.json", params={"linea": "A_regular"}).json()["indicadores"]["total"] == 5
    assert api.get("/panel.json", params={"estado": "vigente"}).json()["indicadores"]["total"] == 4
    assert api.get("/panel.json", params={"estado": "ingreso"}).json()["indicadores"]["total"] == 1


def test_filtro_rango_fechas(api, cartera):
    # sólo los que vencen entre hoy-30 y hoy+60 (C-VENCIDO, C-PORVENCER, C-RENOV)
    d = api.get(
        "/panel.json",
        params={
            "agrupacion": "vencimiento",
            "desde": (HOY - timedelta(days=30)).isoformat(),
            "hasta": (HOY + timedelta(days=60)).isoformat(),
        },
    ).json()
    assert d["indicadores"]["total"] == 3
    assert set(_tarjetas(d)) == {"C-VENCIDO", "C-PORVENCER", "C-RENOV"}


def test_panel_html(api, cartera):
    r = api.get("/panel")
    assert r.status_code == 200
    assert "Panel de Contratos" in r.text
    assert "C-VIG" in r.text
    assert "por vencer" in r.text or "vencido" in r.text


def test_detalle_html(api, cartera):
    r = api.get(f"/panel/contratos/{cartera['RENOV']}")
    assert r.status_code == 200
    assert "C-RENOV" in r.text
    assert "Línea de tiempo" in r.text
    assert "en renovacion" in r.text


def test_raiz_redirige_al_panel(api):
    r = api.get("/")
    assert r.status_code == 200
    assert r.url.path == "/panel"


def test_detalle_404(api):
    assert api.get("/panel/contratos/99999").status_code == 404
