"""Rutas del panel web (HTML server-rendered) y endpoints JSON equivalentes."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_SESION, get_db, obtener_o_404, usuario_actual
from app.config import settings
from app.models.contrato import Contrato
from app.models.core import Contraparte, Unidad, Usuario
from app.services.alertas import calcular_alertas, resumen_alertas
from app.services.auth import crear_token, verify_password
from app.services.consultas import ficha_contrato
from app.services.dashboard import construir_dashboard, opciones_filtros, semaforo_de
from app.services.metricas import metricas_proceso
from app.services.reportes import generar_reporte_mensual

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter(tags=["panel"])


def _to_int(v: Optional[str]) -> Optional[int]:
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _to_date(v: Optional[str]) -> Optional[date]:
    try:
        return date.fromisoformat(v) if v else None
    except (TypeError, ValueError):
        return None


def filtros_panel(
    agrupacion: str = Query("vencimiento"),
    linea: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    unidad_id: Optional[str] = Query(None),
    administrador_id: Optional[str] = Query(None),
    contraparte_id: Optional[str] = Query(None),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
) -> dict:
    return {
        "agrupacion": agrupacion or "vencimiento",
        "linea": linea or None,
        "estado": estado or None,
        "unidad_id": _to_int(unidad_id),
        "administrador_id": _to_int(administrador_id),
        "contraparte_id": _to_int(contraparte_id),
        "desde": _to_date(desde),
        "hasta": _to_date(hasta),
    }


SIN_CACHE = {"Cache-Control": "private, no-store"}


def _requiere_login(request: Request, db: Session) -> Optional[RedirectResponse]:
    if settings.auth_required and usuario_actual(request, db) is None:
        return RedirectResponse(url="/login", status_code=303, headers=SIN_CACHE)
    return None


@router.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/panel")


@router.get("/panel", response_class=HTMLResponse, include_in_schema=False)
def panel(request: Request, filtros: dict = Depends(filtros_panel), db: Session = Depends(get_db)):
    if (r := _requiere_login(request, db)) is not None:
        return r
    datos = construir_dashboard(db, **filtros)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "datos": datos,
            "opciones": opciones_filtros(db),
            "filtros": filtros,
            "alertas": resumen_alertas(db),
        },
        headers=SIN_CACHE,
    )


@router.get("/panel.json", include_in_schema=False)
def panel_json(
    request: Request, filtros: dict = Depends(filtros_panel), db: Session = Depends(get_db)
):
    if settings.auth_required and usuario_actual(request, db) is None:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    return construir_dashboard(db, **filtros)


@router.get("/panel/alertas", response_class=HTMLResponse, include_in_schema=False)
def panel_alertas(request: Request, db: Session = Depends(get_db)):
    if (r := _requiere_login(request, db)) is not None:
        return r
    return templates.TemplateResponse(
        request=request,
        name="alertas.html",
        context={"alertas": calcular_alertas(db), "resumen": resumen_alertas(db)},
        headers=SIN_CACHE,
    )


@router.get("/panel/metricas", response_class=HTMLResponse, include_in_schema=False)
def panel_metricas(request: Request, db: Session = Depends(get_db)):
    if (r := _requiere_login(request, db)) is not None:
        return r
    return templates.TemplateResponse(
        request=request, name="metricas.html", context={"m": metricas_proceso(db)},
        headers=SIN_CACHE,
    )


@router.get("/panel/contratos/{cid}", response_class=HTMLResponse, include_in_schema=False)
def detalle(cid: int, request: Request, db: Session = Depends(get_db)):
    if (r := _requiere_login(request, db)) is not None:
        return r
    contrato = obtener_o_404(db, Contrato, cid, "Contrato")
    ficha = ficha_contrato(db, contrato)
    semaforo, nivel, dias = semaforo_de(db, contrato)

    def _nombre(modelo, ident, attr):
        obj = db.get(modelo, ident) if ident else None
        return getattr(obj, attr) if obj else None

    refs = {
        "contraparte": _nombre(Contraparte, contrato.contraparte_id, "razon_social"),
        "unidad": _nombre(Unidad, contrato.unidad_solicitante_id, "nombre"),
        "administrador": _nombre(Usuario, contrato.administrador_id, "nombre"),
        "abogado": _nombre(Usuario, contrato.abogado_id, "nombre"),
    }
    return templates.TemplateResponse(
        request=request,
        name="detalle.html",
        context={"f": ficha, "refs": refs, "semaforo": semaforo, "nivel": nivel, "dias": dias},
        headers=SIN_CACHE,
    )


@router.get("/panel/reporte", include_in_schema=False)
def descargar_reporte(
    request: Request,
    db: Session = Depends(get_db),
    periodo: str = Query(..., description="AAAA-MM"),
    formato: str = Query("xlsx"),
):
    if (r := _requiere_login(request, db)) is not None:
        return r
    try:
        anio, mes = (int(x) for x in periodo.split("-"))
        contenido, nombre, media = generar_reporte_mensual(db, anio, mes, formato)
    except (ValueError, KeyError):
        return Response("Período o formato inválido (use AAAA-MM y xlsx|pdf)", status_code=400)
    return Response(
        content=contenido,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_form(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": error}
    )


@router.post("/login", include_in_schema=False)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    usuario = db.scalars(select(Usuario).where(Usuario.email == email)).first()
    if usuario is None or not verify_password(password, usuario.password_hash):
        return RedirectResponse(url="/login?error=1", status_code=303)
    if not usuario.activo:
        return RedirectResponse(url="/login?error=inactivo", status_code=303)
    resp = RedirectResponse(url="/panel", status_code=303, headers=SIN_CACHE)
    resp.set_cookie(
        COOKIE_SESION,
        crear_token(usuario.id),
        httponly=True,
        samesite="lax",
        secure=settings.auth_required,  # en producción (AUTH_REQUIRED=true) se sirve por HTTPS
        path="/",
        max_age=8 * 3600,
    )
    return resp


@router.get("/logout", include_in_schema=False)
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(COOKIE_SESION, path="/", samesite="lax", secure=settings.auth_required)
    return resp
