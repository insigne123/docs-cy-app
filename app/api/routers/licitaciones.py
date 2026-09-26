"""API de licitaciones: creación, ficha, transiciones (Fase I) y adjudicación."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import exigir_roles, get_db, obtener_o_404, resolver_actor_transicion, usuario_actual
from app.api.schemas import (
    AdjudicarIn,
    ContratoOut,
    FichaLicitacion,
    GarantiaIn,
    GarantiaOut,
    LicitacionIn,
    LicitacionOut,
    LicitacionUpdate,
    TransicionLicitacionIn,
)
from app.enums import EstadoLicitacion, Rol
from app.models.contrato import Garantia
from app.models.core import Contraparte, Unidad, Usuario
from app.models.licitacion import Licitacion
from app.services.consultas import ficha_licitacion as _ficha
from app.services.licitaciones import adjudicar_licitacion, crear_licitacion
from app.state_machine import MotorEstados

router = APIRouter(prefix="/licitaciones", tags=["licitaciones"])


@router.post("", response_model=LicitacionOut, status_code=201)
def crear(payload: LicitacionIn, db: Session = Depends(get_db)):
    unidad = obtener_o_404(db, Unidad, payload.unidad_solicitante_id, "Unidad")
    solicitante = obtener_o_404(db, Usuario, payload.solicitante_id, "Usuario")
    contraparte = (
        obtener_o_404(db, Contraparte, payload.contraparte_id, "Contraparte")
        if payload.contraparte_id
        else None
    )
    lic = crear_licitacion(
        db,
        codigo=payload.codigo,
        objeto=payload.objeto,
        unidad_solicitante=unidad,
        solicitante=solicitante,
        contraparte=contraparte,
        mandante=payload.mandante,
        moneda=payload.moneda,
        exige_garantia_seriedad=payload.exige_garantia_seriedad,
        fecha_ingreso=payload.fecha_ingreso,
    )
    db.commit()
    db.refresh(lic)
    return lic


@router.get("", response_model=list[LicitacionOut])
def listar(
    db: Session = Depends(get_db),
    estado: Optional[EstadoLicitacion] = None,
    unidad_id: Optional[int] = None,
):
    stmt = select(Licitacion)
    if estado is not None:
        stmt = stmt.where(Licitacion.estado == estado)
    if unidad_id is not None:
        stmt = stmt.where(Licitacion.unidad_solicitante_id == unidad_id)
    return db.scalars(stmt.order_by(Licitacion.id)).all()


@router.get("/{lid}", response_model=FichaLicitacion)
def ficha(lid: int, db: Session = Depends(get_db)):
    lic = obtener_o_404(db, Licitacion, lid, "Licitación")
    return _ficha(db, lic)


@router.patch("/{lid}", response_model=LicitacionOut)
def actualizar(lid: int, payload: LicitacionUpdate, db: Session = Depends(get_db)):
    lic = obtener_o_404(db, Licitacion, lid, "Licitación")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(lic, campo, valor)
    db.commit()
    db.refresh(lic)
    return lic


@router.post("/{lid}/transiciones", response_model=FichaLicitacion)
def transicionar(
    lid: int, payload: TransicionLicitacionIn, db: Session = Depends(get_db),
    sesion_usuario: Optional[Usuario] = Depends(usuario_actual),
):
    lic = obtener_o_404(db, Licitacion, lid, "Licitación")
    usuario, rol = resolver_actor_transicion(db, payload.usuario_id, payload.rol, sesion_usuario)
    MotorEstados(db).transicionar_licitacion(
        lic,
        payload.hacia,
        usuario=usuario,
        rol=rol,
        comentario=payload.comentario,
        extra=dict(payload.extra or {}),
    )
    db.commit()
    db.refresh(lic)
    return _ficha(db, lic)


@router.post("/{lid}/adjudicar", response_model=ContratoOut, status_code=201)
def adjudicar(
    lid: int, payload: AdjudicarIn, db: Session = Depends(get_db),
    sesion_usuario: Optional[Usuario] = Depends(usuario_actual),
):
    lic = obtener_o_404(db, Licitacion, lid, "Licitación")
    usuario, _rol = resolver_actor_transicion(db, payload.usuario_id, None, sesion_usuario)
    contraparte = (
        obtener_o_404(db, Contraparte, payload.contraparte_id, "Contraparte")
        if payload.contraparte_id
        else None
    )
    contrato = adjudicar_licitacion(
        db,
        lic,
        usuario=usuario,
        codigo_contrato=payload.codigo_contrato,
        objeto=payload.objeto,
        contraparte=contraparte,
        comentario=payload.comentario,
    )
    db.commit()
    db.refresh(contrato)
    return contrato


@router.post("/{lid}/garantias", response_model=GarantiaOut, status_code=201)
def agregar_garantia(
    lid: int, payload: GarantiaIn, db: Session = Depends(get_db),
    _=Depends(exigir_roles(Rol.financiera)),
):
    obtener_o_404(db, Licitacion, lid, "Licitación")
    g = Garantia(entidad_tipo="licitacion", entidad_id=lid, **payload.model_dump())
    db.add(g)
    db.commit()
    db.refresh(g)
    return g
