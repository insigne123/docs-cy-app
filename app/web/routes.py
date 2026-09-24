"""Rutas del panel web (HTML server-rendered) y endpoints JSON equivalentes."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_SESION, get_db, obtener_o_404, usuario_actual
from app.config import settings
from app.enums import (
    CategoriaContrato,
    EstadoContrato,
    GarantiaEstado,
    GarantiaInstrumento,
    GarantiaTipo,
    LineaContrato,
    Moneda,
    TipoRenovacion,
    nombre_linea,
)
from app.models.contrato import Contrato, Garantia
from app.models.core import Contraparte, FormatoEstandar, Unidad, Usuario
from app.services.alertas import calcular_alertas, resumen_alertas
from app.services.auth import crear_token, verify_password
from app.services.consultas import ficha_contrato
from app.services.contratos import calcular_requiere_gerencia, crear_contrato, generar_codigo
from app.services.dashboard import construir_dashboard, opciones_filtros, semaforo_de
from app.services.metricas import metricas_proceso
from app.services.reportes import generar_reporte_mensual
from app.state_machine import ErrorTransicion, MotorEstados
from app.state_machine.transitions import transiciones_disponibles

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter(tags=["panel"])

# Sólo estas dos líneas se crean directo como contrato; Flujo Completo (licitación)
# nace como licitación y se convierte en contrato al adjudicarse (ver services/licitaciones.py).
LINEAS_CREABLES = [LineaContrato.A_regular, LineaContrato.B_autogestionado]

_FLAGS_EXTRA = [
    ("borrador_cargado", "Borrador del contrato cargado"),
    ("documento_firmado", "Documento firmado cargado"),
    ("visacion_interna_ok", "Visación interna OK"),
    ("visacion_contraparte_ok", "Visación con la contraparte OK"),
    ("documento_checksum", "Checksum del documento (Línea B) — pegar el hash del formato"),
    ("coherente_con_oferta", "Coherente con la oferta (Gate 1 de licitación)"),
]


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


def _usuario_o_redirect(request: Request, db: Session):
    """Para acciones que escriben (crear/editar/avanzar): siempre exige sesión, aunque
    AUTH_REQUIRED esté apagado — se necesita saber quién hizo el cambio para la
    trazabilidad. Devuelve (usuario, None) o (None, redirect)."""
    usuario = usuario_actual(request, db)
    if usuario is None:
        siguiente = quote(request.url.path, safe="")
        return None, RedirectResponse(url=f"/login?siguiente={siguiente}", status_code=303, headers=SIN_CACHE)
    return usuario, None


def _decimal_o_none(v: Optional[str]) -> Optional[Decimal]:
    if not v:
        return None
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


def _msg(texto) -> str:
    return quote(str(texto), safe="")


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


def _catalogos_basicos(db: Session) -> dict:
    return {
        "unidades": list(db.scalars(select(Unidad).where(Unidad.activo.is_(True)).order_by(Unidad.nombre))),
        "contrapartes": list(db.scalars(select(Contraparte).order_by(Contraparte.razon_social))),
        "usuarios": list(db.scalars(select(Usuario).where(Usuario.activo.is_(True)).order_by(Usuario.nombre))),
        "formatos": list(
            db.scalars(select(FormatoEstandar).where(FormatoEstandar.vigente.is_(True)).order_by(FormatoEstandar.nombre))
        ),
    }


@router.get("/panel/contratos/nuevo", response_class=HTMLResponse, include_in_schema=False)
def nuevo_contrato_form(request: Request, db: Session = Depends(get_db), error: Optional[str] = None):
    usuario, r = _usuario_o_redirect(request, db)
    if r is not None:
        return r
    return templates.TemplateResponse(
        request=request,
        name="nuevo_contrato.html",
        context={
            "usuario": usuario,
            "lineas": LINEAS_CREABLES,
            "nombre_linea": nombre_linea,
            "categorias": list(CategoriaContrato),
            "monedas": list(Moneda),
            "error": error,
            **_catalogos_basicos(db),
        },
        headers=SIN_CACHE,
    )


@router.post("/panel/contratos/nuevo", include_in_schema=False)
def nuevo_contrato_submit(
    request: Request,
    db: Session = Depends(get_db),
    linea: str = Form(...),
    objeto: str = Form(...),
    unidad_solicitante_id: int = Form(...),
    contraparte_id: Optional[str] = Form(None),
    formato_id: Optional[str] = Form(None),
    categoria: Optional[str] = Form(None),
    monto: Optional[str] = Form(None),
    moneda: Optional[str] = Form(None),
    requiere_garantia: Optional[str] = Form(None),
):
    usuario, r = _usuario_o_redirect(request, db)
    if r is not None:
        return r
    unidad = db.get(Unidad, unidad_solicitante_id)
    contraparte = db.get(Contraparte, int(contraparte_id)) if contraparte_id else None
    formato = db.get(FormatoEstandar, int(formato_id)) if formato_id else None
    if unidad is None:
        return RedirectResponse(url=f"/panel/contratos/nuevo?error={_msg('Unidad inválida')}", status_code=303)
    try:
        contrato = crear_contrato(
            db,
            codigo=generar_codigo(db),
            linea=LineaContrato(linea),
            objeto=objeto,
            unidad_solicitante=unidad,
            solicitante=usuario,
            contraparte=contraparte,
            formato=formato,
            categoria=CategoriaContrato(categoria) if categoria else None,
            monto=_decimal_o_none(monto),
            moneda=Moneda(moneda) if moneda else None,
            requiere_garantia=bool(requiere_garantia),
        )
    except ValueError as exc:
        return RedirectResponse(url=f"/panel/contratos/nuevo?error={_msg(exc)}", status_code=303)
    db.commit()
    return RedirectResponse(url=f"/panel/contratos/{contrato.id}?ok={_msg('Contrato creado')}", status_code=303)


@router.get("/panel/contratos/{cid}", response_class=HTMLResponse, include_in_schema=False)
def detalle(
    cid: int,
    request: Request,
    db: Session = Depends(get_db),
    error: Optional[str] = None,
    ok: Optional[str] = None,
):
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
        "linea_nombre": nombre_linea(contrato.linea.value),
    }

    estado_actual = contrato.estado.value
    if estado_actual in ("terminado", "descartado"):
        opciones_transicion = []
    elif estado_actual == "aclaraciones":
        opciones_transicion = [contrato.retorno_a] if contrato.retorno_a else []
    else:
        opciones_transicion = transiciones_disponibles(estado_actual, contrato.linea.value)
    puede_descartar = estado_actual not in ("terminado", "descartado")

    return templates.TemplateResponse(
        request=request,
        name="detalle.html",
        context={
            "f": ficha, "refs": refs, "semaforo": semaforo, "nivel": nivel, "dias": dias,
            "error": error, "ok": ok,
            "opciones_transicion": opciones_transicion,
            "puede_descartar": puede_descartar,
            "flags_extra": _FLAGS_EXTRA,
            "categorias": list(CategoriaContrato),
            "monedas": list(Moneda),
            "renovaciones": list(TipoRenovacion),
            "garantia_tipos": list(GarantiaTipo),
            "garantia_instrumentos": list(GarantiaInstrumento),
            **_catalogos_basicos(db),
        },
        headers=SIN_CACHE,
    )


@router.post("/panel/contratos/{cid}/editar", include_in_schema=False)
def editar_contrato_submit(
    cid: int,
    request: Request,
    db: Session = Depends(get_db),
    contraparte_id: Optional[str] = Form(None),
    abogado_id: Optional[str] = Form(None),
    administrador_id: Optional[str] = Form(None),
    monto: Optional[str] = Form(None),
    moneda: Optional[str] = Form(None),
    requiere_garantia: Optional[str] = Form(None),
    vigencia_indefinida: Optional[str] = Form(None),
    fecha_inicio_vigencia: Optional[str] = Form(None),
    fecha_fin_vigencia: Optional[str] = Form(None),
    tipo_renovacion: Optional[str] = Form(None),
    aviso_previo_dias: Optional[str] = Form(None),
    causales_termino: Optional[str] = Form(None),
):
    usuario, r = _usuario_o_redirect(request, db)
    if r is not None:
        return r
    contrato = obtener_o_404(db, Contrato, cid, "Contrato")

    contrato.contraparte_id = int(contraparte_id) if contraparte_id else None
    contrato.abogado_id = int(abogado_id) if abogado_id else None
    contrato.administrador_id = int(administrador_id) if administrador_id else None
    contrato.monto = _decimal_o_none(monto)
    contrato.moneda = Moneda(moneda) if moneda else None
    contrato.requiere_garantia = bool(requiere_garantia)
    contrato.vigencia_indefinida = bool(vigencia_indefinida)
    contrato.fecha_inicio_vigencia = _to_date(fecha_inicio_vigencia)
    contrato.fecha_fin_vigencia = _to_date(fecha_fin_vigencia)
    contrato.tipo_renovacion = TipoRenovacion(tipo_renovacion) if tipo_renovacion else contrato.tipo_renovacion
    if aviso_previo_dias:
        contrato.aviso_previo_dias = int(aviso_previo_dias)
    contrato.causales_termino = causales_termino or None
    contrato.requiere_aprobacion_gerencia = calcular_requiere_gerencia(
        db, contrato.monto, contrato.moneda, contrato.monto_referencia_clp
    )
    db.commit()
    return RedirectResponse(url=f"/panel/contratos/{cid}?ok={_msg('Datos actualizados')}", status_code=303)


@router.post("/panel/contratos/{cid}/garantias", include_in_schema=False)
def agregar_garantia_submit(
    cid: int,
    request: Request,
    db: Session = Depends(get_db),
    tipo: str = Form(...),
    instrumento: str = Form(...),
    monto: str = Form(...),
    moneda: str = Form(...),
    fecha_emision: str = Form(...),
    fecha_vencimiento: str = Form(...),
    emisor: Optional[str] = Form(None),
    numero: Optional[str] = Form(None),
):
    _, r = _usuario_o_redirect(request, db)
    if r is not None:
        return r
    obtener_o_404(db, Contrato, cid, "Contrato")
    try:
        db.add(
            Garantia(
                entidad_tipo="contrato",
                entidad_id=cid,
                tipo=GarantiaTipo(tipo),
                instrumento=GarantiaInstrumento(instrumento),
                emisor=emisor or None,
                numero=numero or None,
                monto=Decimal(monto),
                moneda=Moneda(moneda),
                fecha_emision=date.fromisoformat(fecha_emision),
                fecha_vencimiento=date.fromisoformat(fecha_vencimiento),
                estado=GarantiaEstado.vigente,
            )
        )
        db.commit()
    except (ValueError, InvalidOperation) as exc:
        return RedirectResponse(url=f"/panel/contratos/{cid}?error={_msg('Garantía inválida: ' + str(exc))}", status_code=303)
    return RedirectResponse(url=f"/panel/contratos/{cid}?ok={_msg('Garantía agregada')}", status_code=303)


@router.post("/panel/contratos/{cid}/transicion", include_in_schema=False)
async def transicion_submit(cid: int, request: Request, db: Session = Depends(get_db)):
    usuario, r = _usuario_o_redirect(request, db)
    if r is not None:
        return r
    contrato = obtener_o_404(db, Contrato, cid, "Contrato")

    form = await request.form()
    hacia = form.get("hacia")
    comentario = (form.get("comentario") or None) and str(form.get("comentario"))
    if not hacia:
        return RedirectResponse(url=f"/panel/contratos/{cid}?error={_msg('Falta elegir un estado destino')}", status_code=303)

    extra: dict = {}
    if contrato.estado.value == "ingreso":
        # Único punto donde importa: ir a 'aclaraciones' desde 'ingreso' EXIGE
        # completitud_ok=False; cualquier otro destino exige True. Se deriva de la
        # elección del usuario en vez de pedir un checkbox aparte (evita el estado
        # "ambos ausentes" que un checkbox no puede expresar).
        extra["completitud_ok"] = hacia != "aclaraciones"
    for clave, _etiqueta in _FLAGS_EXTRA:
        valor = form.get(clave)
        if not valor:
            continue
        extra[clave] = str(valor) if clave == "documento_checksum" else True
    if form.get("nueva_fecha_fin"):
        try:
            extra["nueva_fecha_fin"] = date.fromisoformat(str(form.get("nueva_fecha_fin")))
        except ValueError:
            pass
    if form.get("analisis_interno"):
        extra["analisis_interno"] = str(form.get("analisis_interno"))

    try:
        MotorEstados(db).transicionar_contrato(
            contrato, EstadoContrato(str(hacia)), usuario=usuario, comentario=comentario, extra=extra,
        )
        db.commit()
    except ErrorTransicion as exc:
        return RedirectResponse(url=f"/panel/contratos/{cid}?error={_msg(exc)}", status_code=303)
    except ValueError as exc:
        return RedirectResponse(url=f"/panel/contratos/{cid}?error={_msg('Estado inválido: ' + str(exc))}", status_code=303)
    return RedirectResponse(url=f"/panel/contratos/{cid}?ok={_msg('Estado actualizado')}", status_code=303)


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
def login_form(request: Request, error: Optional[str] = None, siguiente: Optional[str] = None):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": error, "siguiente": siguiente}
    )


@router.post("/login", include_in_schema=False)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    siguiente: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    destino = siguiente if siguiente and siguiente.startswith("/") else "/panel"
    email = email.strip().lower()
    usuario = db.scalars(select(Usuario).where(Usuario.email == email)).first()
    if usuario is None or not verify_password(password, usuario.password_hash):
        return RedirectResponse(url=f"/login?error=1&siguiente={quote(destino, safe='')}", status_code=303)
    if not usuario.activo:
        return RedirectResponse(url=f"/login?error=inactivo&siguiente={quote(destino, safe='')}", status_code=303)
    resp = RedirectResponse(url=destino, status_code=303, headers=SIN_CACHE)
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
