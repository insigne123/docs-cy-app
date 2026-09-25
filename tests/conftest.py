"""Fixtures compartidas de las pruebas."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  registra todos los modelos en la metadata
from app.enums import (
    ContraparteTipo,
    EstadoContrato,
    LineaContrato,
    Moneda,
    Rol,
    TipoRenovacion,
    UnidadTipo,
)
from app.models.base import Base
from app.models.core import Contraparte, FormatoEstandar, Unidad, Usuario
from app.services.contratos import crear_contrato
from app.services.parametros import sembrar_parametros
from app.state_machine import MotorEstados


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    # Igual que app/database.py: SQLite no aplica FOREIGN KEY por defecto. Sin esto,
    # borrar una fila referenciada (ej. una Contraparte en uso) no falla en las
    # pruebas aunque sí fallaría en Postgres (producción) — un falso negativo.
    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_connection, connection_record):  # pragma: no cover
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = factory()
    sembrar_parametros(s)
    s.commit()
    try:
        yield s
    finally:
        s.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def unidad(session: Session) -> Unidad:
    u = Unidad(nombre="Operaciones", tipo=UnidadTipo.solicitante)
    session.add(u)
    session.commit()
    return u


@pytest.fixture()
def usuarios(session: Session, unidad: Unidad) -> dict[Rol, Usuario]:
    creados: dict[Rol, Usuario] = {}
    for rol in Rol:
        u = Usuario(nombre=rol.value, email=f"{rol.value}@empresa.cl", rol=rol, unidad_id=unidad.id)
        session.add(u)
        creados[rol] = u
    session.commit()
    return creados


@pytest.fixture()
def contraparte(session: Session) -> Contraparte:
    c = Contraparte(razon_social="Aseos del Sur SpA", tipo=ContraparteTipo.proveedor)
    session.add(c)
    session.commit()
    return c


@pytest.fixture()
def api(session: Session):
    """Cliente HTTP de pruebas con la sesión de test inyectada en la API."""
    from fastapi.testclient import TestClient

    from app.api.app import create_app
    from app.api.deps import get_db

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def formato(session: Session) -> FormatoEstandar:
    f = FormatoEstandar(
        nombre="NDA estandar",
        version=3,
        vigente=True,
        aprobado_por="Fiscalia",
        fecha_aprobacion=date(2025, 1, 1),
        campos_variables=["contraparte", "fecha"],
        ruta_plantilla="formatos/nda_v3.docx",
        checksum_base="abc123",
    )
    session.add(f)
    session.commit()
    return f


@pytest.fixture()
def cartera(session, usuarios, unidad, contraparte):
    """Cinco contratos que cubren cada estado del semáforo (VIG, PORVENCER, VENCIDO,
    RENOV, TRAMITE). Devuelve {clave: id}."""
    from tests._helpers import avanzar_a

    hoy = date.today()
    motor = MotorEstados(session)

    def vigente(codigo, fin, renov=TipoRenovacion.sin_renovacion, ingreso=date(2026, 1, 15)):
        c = crear_contrato(
            session, codigo=codigo, linea=LineaContrato.A_regular, objeto=f"Objeto {codigo}",
            unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante],
            contraparte=contraparte, monto=1_000_000, moneda=Moneda.CLP, fecha_ingreso=ingreso,
        )
        avanzar_a(motor, c, usuarios, EstadoContrato.vigente)
        c.fecha_fin_vigencia = fin
        c.tipo_renovacion = renov
        return c

    ids = {
        "VIG": vigente("C-VIG", hoy + timedelta(days=400)).id,
        "PORVENCER": vigente("C-PORVENCER", hoy + timedelta(days=20)).id,
        "VENCIDO": vigente("C-VENCIDO", hoy - timedelta(days=10)).id,
        "RENOV": vigente("C-RENOV", hoy + timedelta(days=45), TipoRenovacion.automatica).id,
    }
    tramite = crear_contrato(
        session, codigo="C-TRAMITE", linea=LineaContrato.A_regular, objeto="En trámite",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante],
        contraparte=contraparte, fecha_ingreso=date(2026, 2, 1),
    )
    ids["TRAMITE"] = tramite.id
    session.commit()
    return ids
