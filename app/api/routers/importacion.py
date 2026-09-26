"""API de importación masiva desde planilla."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import exigir_admin_sistema, get_db
from app.api.schemas import ImportarIn, ResultadoImportacionOut
from app.services.importador import importar_planilla_contratos

router = APIRouter(prefix="/importaciones", tags=["importación"])

_CARPETA_DEFECTO = Path("Contratos/Planillas")


@router.post("/contratos", response_model=ResultadoImportacionOut)
def importar_contratos(
    payload: ImportarIn, db: Session = Depends(get_db), _=Depends(exigir_admin_sistema),
):
    # carpeta/archivo aceptan cualquier ruta local a propósito (carga inicial
    # y recargas posteriores desde donde sea que viva la planilla en el
    # servidor) — por eso esto queda restringido a admin_sistema en vez de
    # limitarse a una carpeta fija: antes cualquier usuario autenticado, de
    # cualquier rol, podía leer archivos arbitrarios del contenedor con solo
    # cambiar 'carpeta'/'archivo'.
    carpeta = Path(payload.carpeta) if payload.carpeta else _CARPETA_DEFECTO
    ruta = carpeta / payload.archivo
    if not ruta.exists():
        raise HTTPException(status_code=404, detail=f"No existe el archivo: {ruta}")
    if ruta.suffix.lower() not in (".xlsx", ".csv"):
        raise HTTPException(status_code=400, detail="Formato no soportado (use .xlsx o .csv)")
    resultado = importar_planilla_contratos(db, ruta)
    db.commit()
    return resultado.resumen()
