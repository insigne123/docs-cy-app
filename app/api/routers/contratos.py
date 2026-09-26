"""API de contratos: creación, ficha, transiciones de estado y sub-recursos."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, obtener_o_404, resolver_actor_transicion, usuario_actual
from app.api.schemas import (
    ContratoIn,
    ContratoOut,
    ContratoUpdate,
    DocumentoIn,
    DocumentoOut,
    FichaContrato,
    GarantiaIn,
    GarantiaOut,
    HitoIn,
    HitoOut,
    MultaIn,
    MultaOut,
    TransicionIn,
)
from app.enums import EstadoContrato, LineaContrato
from app.models.contrato import Contrato, Documento, Garantia, Hito, Multa
from app.models.core import Contraparte, FormatoEstandar, Unidad, Usuario
from app.services.consultas import ficha_contrato as _ficha
from app.services.contratos import calcular_requiere_gerencia, crear_contrato
from app.state_machine import MotorEstados

router = APIRouter(prefix="/contratos", tags=["contratos"])


@router.post("", response_model=ContratoOut, status_code=201)
def crear(payload: ContratoIn, db: Session = Depends(get_db)):
    unidad = obtener_o_404(db, Unidad, payload.unidad_solicitante_id, "Unidad")
    solicitante = obtener_o_404(db, Usuario, payload.solicitante_id, "Usuario")
    contraparte = (
        obtener_o_404(db, Contraparte, payload.contraparte_id, "Contraparte")
        if payload.contraparte_id
        else None
    )
    formato = (
        obtener_o_404(db, FormatoEstandar, payload.formato_id, "Formato")
        if payload.formato_id
        else None
    )
    try:
        contrato = crear_contrato(
            db,
            codigo=payload.codigo,
            linea=payload.linea,
            objeto=payload.objeto,
            unidad_solicitante=unidad,
            solicitante=solicitante,
            contraparte=contraparte,
            formato=formato,
            categoria=payload.categoria,
            monto=payload.monto,
            moneda=payload.moneda,
            monto_referencia_clp=payload.monto_referencia_clp,
            requiere_garantia=payload.requiere_garantia,
            requiere_visacion_contraparte=payload.requiere_visacion_contraparte,
            fecha_ingreso=payload.fecha_ingreso,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(contrato)
    return contrato


@router.get("", response_model=list[ContratoOut])
def listar(
    db: Session = Depends(get_db),
    linea: Optional[LineaContrato] = None,
    estado: Optional[EstadoContrato] = None,
    unidad_id: Optional[int] = None,
    contraparte_id: Optional[int] = None,
    administrador_id: Optional[int] = None,
    abogado_id: Optional[int] = None,
):
    stmt = select(Contrato)
    if linea is not None:
        stmt = stmt.where(Contrato.linea == linea)
    if estado is not None:
        stmt = stmt.where(Contrato.estado == estado)
    if unidad_id is not None:
        stmt = stmt.where(Contrato.unidad_solicitante_id == unidad_id)
    if contraparte_id is not None:
        stmt = stmt.where(Contrato.contraparte_id == contraparte_id)
    if administrador_id is not None:
        stmt = stmt.where(Contrato.administrador_id == administrador_id)
    if abogado_id is not None:
        stmt = stmt.where(Contrato.abogado_id == abogado_id)
    return db.scalars(stmt.order_by(Contrato.id)).all()


@router.get("/{cid}", response_model=FichaContrato)
def ficha(cid: int, db: Session = Depends(get_db)):
    contrato = obtener_o_404(db, Contrato, cid, "Contrato")
    return _ficha(db, contrato)


@router.patch("/{cid}", response_model=ContratoOut)
def actualizar(cid: int, payload: ContratoUpdate, db: Session = Depends(get_db)):
    contrato = obtener_o_404(db, Contrato, cid, "Contrato")
    datos = payload.model_dump(exclude_unset=True)
    for campo in ("contraparte_id", "abogado_id", "administrador_id"):
        if campo in datos and datos[campo] is not None:
            modelo = Contraparte if campo == "contraparte_id" else Usuario
            obtener_o_404(db, modelo, datos[campo], modelo.__name__)
    for campo, valor in datos.items():
        setattr(contrato, campo, valor)
    if {"monto", "moneda", "monto_referencia_clp"} & datos.keys():
        contrato.requiere_aprobacion_gerencia = calcular_requiere_gerencia(
            db, contrato.monto, contrato.moneda, contrato.monto_referencia_clp
        )
    db.commit()
    db.refresh(contrato)
    return contrato


@router.post("/{cid}/transiciones", response_model=FichaContrato)
def transicionar(
    cid: int, payload: TransicionIn, db: Session = Depends(get_db),
    sesion_usuario: Optional[Usuario] = Depends(usuario_actual),
):
    contrato = obtener_o_404(db, Contrato, cid, "Contrato")
    usuario, rol = resolver_actor_transicion(db, payload.usuario_id, payload.rol, sesion_usuario)
    try:
        hacia = EstadoContrato(payload.hacia)
        retorno_a = EstadoContrato(payload.retorno_a) if payload.retorno_a else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Estado desconocido: {exc}") from exc

    extra = dict(payload.extra or {})
    if isinstance(extra.get("nueva_fecha_fin"), str):
        try:
            extra["nueva_fecha_fin"] = date.fromisoformat(extra["nueva_fecha_fin"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="nueva_fecha_fin inválida") from exc

    MotorEstados(db).transicionar_contrato(
        contrato,
        hacia,
        usuario=usuario,
        rol=rol,
        comentario=payload.comentario,
        retorno_a=retorno_a,
        extra=extra,
    )
    db.commit()
    db.refresh(contrato)
    return _ficha(db, contrato)


@router.get("/{cid}/historial", response_model=list)
def historial(cid: int, db: Session = Depends(get_db)):
    contrato = obtener_o_404(db, Contrato, cid, "Contrato")
    return [
        {
            "estado_origen": e.estado_origen,
            "estado_destino": e.estado_destino,
            "fecha": e.fecha,
            "rol_actor": e.rol_actor,
            "usuario_id": e.usuario_id,
            "comentario": e.comentario,
            "retorno_a": e.retorno_a,
        }
        for e in MotorEstados(db).historial(contrato)
    ]


@router.post("/{cid}/garantias", response_model=GarantiaOut, status_code=201)
def agregar_garantia(cid: int, payload: GarantiaIn, db: Session = Depends(get_db)):
    obtener_o_404(db, Contrato, cid, "Contrato")
    g = Garantia(entidad_tipo="contrato", entidad_id=cid, **payload.model_dump())
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@router.post("/{cid}/hitos", response_model=HitoOut, status_code=201)
def agregar_hito(cid: int, payload: HitoIn, db: Session = Depends(get_db)):
    obtener_o_404(db, Contrato, cid, "Contrato")
    h = Hito(contrato_id=cid, **payload.model_dump())
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@router.post("/{cid}/multas", response_model=MultaOut, status_code=201)
def agregar_multa(cid: int, payload: MultaIn, db: Session = Depends(get_db)):
    obtener_o_404(db, Contrato, cid, "Contrato")
    m = Multa(contrato_id=cid, **payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.post("/{cid}/documentos", response_model=DocumentoOut, status_code=201)
def agregar_documento(cid: int, payload: DocumentoIn, db: Session = Depends(get_db)):
    obtener_o_404(db, Contrato, cid, "Contrato")
    d = Documento(entidad_tipo="contrato", entidad_id=cid, **payload.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d
