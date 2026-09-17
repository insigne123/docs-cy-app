"""Demostración manual de los flujos A, B y C sobre una base SQLite en memoria.

Uso:
    python -m scripts.demo_flujos

No toca ninguna base real: crea todo en memoria, ejecuta los recorridos y muestra
la trazabilidad de cada expediente.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  registra la metadata
from app.enums import (
    ContraparteTipo,
    EstadoContrato,
    EstadoLicitacion,
    GarantiaEstado,
    GarantiaInstrumento,
    GarantiaTipo,
    LineaContrato,
    Moneda,
    Rol,
    UnidadTipo,
)
from app.models.base import Base
from app.models.contrato import Garantia
from app.models.core import Contraparte, FormatoEstandar, Unidad, Usuario
from app.services.contratos import crear_contrato
from app.services.licitaciones import adjudicar_licitacion, crear_licitacion
from app.services.parametros import sembrar_parametros
from app.state_machine import MotorEstados


def _nueva_sesion():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)()


def _mostrar(motor: MotorEstados, entidad, titulo: str) -> None:
    print(f"\n=== {titulo} ===")
    for e in motor.historial(entidad):
        origen = e.estado_origen or "(inicio)"
        print(f"  {origen:>22}  ->  {e.estado_destino:<22}  [{e.rol_actor}]  {e.comentario or ''}")


def main() -> None:
    s = _nueva_sesion()
    sembrar_parametros(s)

    unidad = Unidad(nombre="Operaciones", tipo=UnidadTipo.solicitante)
    s.add(unidad)
    s.flush()
    usuarios = {}
    for rol in Rol:
        u = Usuario(nombre=rol.value, email=f"{rol.value}@empresa.cl", rol=rol, unidad_id=unidad.id)
        s.add(u)
        usuarios[rol] = u
    contraparte = Contraparte(razon_social="Aseos del Sur SpA", tipo=ContraparteTipo.proveedor)
    formato = FormatoEstandar(
        nombre="NDA estandar",
        version=3,
        vigente=True,
        aprobado_por="Fiscalia",
        fecha_aprobacion=date(2025, 1, 1),
        campos_variables=["contraparte", "fecha"],
        ruta_plantilla="formatos/nda_v3.docx",
        checksum_base="abc123",
    )
    s.add_all([contraparte, formato])
    s.flush()

    motor = MotorEstados(s)
    us = usuarios

    # ---------------- Línea A
    ca = crear_contrato(
        s, codigo="CT-2026-0001", linea=LineaContrato.A_regular, objeto="Servicio de aseo",
        unidad_solicitante=unidad, solicitante=us[Rol.unidad_solicitante], contraparte=contraparte,
        monto=1_000_000, moneda=Moneda.CLP,
    )
    motor.transicionar_contrato(ca, EstadoContrato.aprobacion_jefatura, usuario=us[Rol.unidad_solicitante])
    motor.transicionar_contrato(ca, EstadoContrato.admisibilidad_1, usuario=us[Rol.jefatura])
    motor.transicionar_contrato(ca, EstadoContrato.admisibilidad_2, usuario=us[Rol.legal])
    ca.abogado_id = us[Rol.legal].id
    motor.transicionar_contrato(ca, EstadoContrato.elaboracion, usuario=us[Rol.legal])
    motor.transicionar_contrato(ca, EstadoContrato.visacion, usuario=us[Rol.legal], extra={"borrador_cargado": True})
    motor.transicionar_contrato(ca, EstadoContrato.firma, usuario=us[Rol.legal])
    motor.transicionar_contrato(ca, EstadoContrato.integracion, usuario=us[Rol.legal], extra={"documento_firmado": True})
    ca.administrador_id = us[Rol.admin_contratos].id
    ca.fecha_fin_vigencia = date(2027, 1, 1)
    motor.transicionar_contrato(ca, EstadoContrato.vigente, usuario=us[Rol.admin_contratos])
    _mostrar(motor, ca, f"Línea A  (estado final: {ca.estado.value})")

    # ---------------- Línea B
    cb = crear_contrato(
        s, codigo="CT-2026-0002", linea=LineaContrato.B_autogestionado, objeto="NDA proveedor X",
        unidad_solicitante=unidad, solicitante=us[Rol.unidad_solicitante], contraparte=contraparte,
        formato=formato, monto=500_000, moneda=Moneda.CLP,
    )
    motor.transicionar_contrato(cb, EstadoContrato.admisibilidad_1, usuario=us[Rol.unidad_solicitante])
    motor.transicionar_contrato(cb, EstadoContrato.visacion, usuario=us[Rol.legal], extra={"documento_checksum": "abc123"})
    motor.transicionar_contrato(cb, EstadoContrato.firma, usuario=us[Rol.legal])
    motor.transicionar_contrato(cb, EstadoContrato.integracion, usuario=us[Rol.legal], extra={"documento_firmado": True})
    cb.administrador_id = us[Rol.admin_contratos].id
    cb.vigencia_indefinida = True
    motor.transicionar_contrato(cb, EstadoContrato.vigente, usuario=us[Rol.admin_contratos])
    _mostrar(motor, cb, f"Línea B  (estado final: {cb.estado.value})")

    # ---------------- Línea C
    lic = crear_licitacion(
        s, codigo="LIC-2026-0001", objeto="Mantención flota", unidad_solicitante=unidad,
        solicitante=us[Rol.admin_licitaciones], moneda=Moneda.CLP,
    )
    motor.transicionar_licitacion(lic, EstadoLicitacion.examen_admisibilidad, usuario=us[Rol.admin_licitaciones])
    motor.transicionar_licitacion(lic, EstadoLicitacion.revision_bases, usuario=us[Rol.legal])
    motor.transicionar_licitacion(lic, EstadoLicitacion.preparacion_oferta, usuario=us[Rol.legal], extra={"informe_riesgos_ok": True})
    motor.transicionar_licitacion(
        lic, EstadoLicitacion.presentacion_oferta, usuario=us[Rol.tecnica],
        extra={"oferta_tecnica_ok": True, "oferta_economica_ok": True},
    )
    motor.transicionar_licitacion(lic, EstadoLicitacion.evaluacion_resultado, usuario=us[Rol.admin_licitaciones])
    cc = adjudicar_licitacion(s, lic, usuario=us[Rol.admin_licitaciones], codigo_contrato="CT-2026-0003")
    motor.transicionar_contrato(cc, EstadoContrato.constitucion_garantias, usuario=us[Rol.legal], extra={"coherente_con_oferta": True})
    s.add(
        Garantia(
            entidad_tipo="contrato", entidad_id=cc.id, tipo=GarantiaTipo.fiel_cumplimiento,
            instrumento=GarantiaInstrumento.boleta_bancaria, monto=1_000_000, moneda=Moneda.CLP,
            fecha_emision=date(2026, 1, 1), fecha_vencimiento=date(2027, 6, 1), estado=GarantiaEstado.vigente,
        )
    )
    s.flush()
    motor.transicionar_contrato(cc, EstadoContrato.firma, usuario=us[Rol.financiera])
    motor.transicionar_contrato(cc, EstadoContrato.integracion, usuario=us[Rol.legal], extra={"documento_firmado": True})
    cc.administrador_id = us[Rol.admin_contratos].id
    cc.fecha_fin_vigencia = date(2028, 1, 1)
    motor.transicionar_contrato(cc, EstadoContrato.vigente, usuario=us[Rol.admin_contratos])
    _mostrar(motor, lic, f"Línea C - Fase I  (resultado: {lic.resultado.value})")
    _mostrar(motor, cc, f"Línea C - Fase II  (estado final: {cc.estado.value})")

    s.commit()
    print("\nOK: los tres flujos se completaron.")


if __name__ == "__main__":
    main()
