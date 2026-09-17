"""CRUD de catálogos: unidades, usuarios, contrapartes, formatos, parámetros."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, obtener_o_404
from app.api.schemas import (
    ContraparteIn,
    ContraparteOut,
    FormatoIn,
    FormatoOut,
    ParametroOut,
    ParametroUpdate,
    UnidadIn,
    UnidadOut,
    UsuarioIn,
    UsuarioOut,
)
from app.models.core import Contraparte, FormatoEstandar, Parametro, Unidad, Usuario
from app.services.auth import hash_password
from app.services.formatos import verificar_formato

router = APIRouter(tags=["catálogos"])


def _guardar(db: Session, obj):
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Conflicto de unicidad: {exc.orig}") from exc
    db.refresh(obj)
    return obj


# ---------------- unidades
@router.post("/unidades", response_model=UnidadOut, status_code=201)
def crear_unidad(payload: UnidadIn, db: Session = Depends(get_db)):
    return _guardar(db, Unidad(**payload.model_dump()))


@router.get("/unidades", response_model=list[UnidadOut])
def listar_unidades(db: Session = Depends(get_db)):
    return db.scalars(select(Unidad).order_by(Unidad.id)).all()


@router.get("/unidades/{uid}", response_model=UnidadOut)
def obtener_unidad(uid: int, db: Session = Depends(get_db)):
    return obtener_o_404(db, Unidad, uid, "Unidad")


# ---------------- usuarios
@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def crear_usuario(payload: UsuarioIn, db: Session = Depends(get_db)):
    datos = payload.model_dump()
    clave = datos.pop("password", None)
    usuario = Usuario(**datos)
    if clave:
        usuario.password_hash = hash_password(clave)
    return _guardar(db, usuario)


@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.scalars(select(Usuario).order_by(Usuario.id)).all()


@router.get("/usuarios/{uid}", response_model=UsuarioOut)
def obtener_usuario(uid: int, db: Session = Depends(get_db)):
    return obtener_o_404(db, Usuario, uid, "Usuario")


# ---------------- contrapartes
@router.post("/contrapartes", response_model=ContraparteOut, status_code=201)
def crear_contraparte(payload: ContraparteIn, db: Session = Depends(get_db)):
    return _guardar(db, Contraparte(**payload.model_dump()))


@router.get("/contrapartes", response_model=list[ContraparteOut])
def listar_contrapartes(db: Session = Depends(get_db)):
    return db.scalars(select(Contraparte).order_by(Contraparte.id)).all()


@router.get("/contrapartes/{cid}", response_model=ContraparteOut)
def obtener_contraparte(cid: int, db: Session = Depends(get_db)):
    return obtener_o_404(db, Contraparte, cid, "Contraparte")


# ---------------- formatos estándar (Línea B)
@router.post("/formatos", response_model=FormatoOut, status_code=201)
def crear_formato(payload: FormatoIn, db: Session = Depends(get_db)):
    return _guardar(db, FormatoEstandar(**payload.model_dump()))


@router.get("/formatos", response_model=list[FormatoOut])
def listar_formatos(db: Session = Depends(get_db)):
    return db.scalars(select(FormatoEstandar).order_by(FormatoEstandar.id)).all()


@router.post("/formatos/{fid}/verificar")
def verificar_formato_endpoint(
    fid: int, archivo: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Compara el SHA-256 del archivo subido con el clausulado estándar (Línea B)."""
    obtener_o_404(db, FormatoEstandar, fid, "Formato")
    try:
        return verificar_formato(db, fid, archivo.file.read())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------- parámetros
@router.get("/parametros", response_model=list[ParametroOut])
def listar_parametros(db: Session = Depends(get_db)):
    return db.scalars(select(Parametro).order_by(Parametro.clave)).all()


@router.put("/parametros/{clave}", response_model=ParametroOut)
def actualizar_parametro(clave: str, payload: ParametroUpdate, db: Session = Depends(get_db)):
    p = obtener_o_404(db, Parametro, clave, "Parámetro")
    p.valor = payload.valor
    db.commit()
    db.refresh(p)
    return p
