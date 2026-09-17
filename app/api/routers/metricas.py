"""API de métricas de proceso."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.metricas import metricas_proceso

router = APIRouter(prefix="/metricas", tags=["métricas"])


@router.get("")
def metricas(db: Session = Depends(get_db)):
    return metricas_proceso(db)
