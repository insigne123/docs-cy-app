"""API de alertas (calculadas al vuelo)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.alertas import calcular_alertas, resumen_alertas

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get("")
def listar(
    db: Session = Depends(get_db),
    tipo: Optional[str] = None,
    nivel: Optional[str] = None,
):
    return calcular_alertas(db, tipo=tipo, nivel=nivel)


@router.get("/resumen")
def resumen(db: Session = Depends(get_db)):
    return resumen_alertas(db)
