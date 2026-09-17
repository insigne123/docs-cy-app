"""Utilidades para las pruebas del motor de estados."""
from __future__ import annotations

from datetime import date

from app.enums import EstadoContrato, LineaContrato, Moneda, Rol
from app.services.contratos import crear_contrato
from app.state_machine import MotorEstados

_ORDEN_A = [
    EstadoContrato.aprobacion_jefatura,
    EstadoContrato.admisibilidad_1,
    EstadoContrato.admisibilidad_2,
    EstadoContrato.elaboracion,
    EstadoContrato.visacion,
    EstadoContrato.firma,
    EstadoContrato.integracion,
    EstadoContrato.vigente,
]


def crear_contrato_a(session, usuarios, unidad, contraparte, *, codigo="CT-TEST-A", monto=1_000_000):
    return crear_contrato(
        session,
        codigo=codigo,
        linea=LineaContrato.A_regular,
        objeto="Contrato de prueba",
        unidad_solicitante=unidad,
        solicitante=usuarios[Rol.unidad_solicitante],
        contraparte=contraparte,
        monto=monto,
        moneda=Moneda.CLP,
    )


def avanzar_a(motor: MotorEstados, contrato, usuarios, hasta: EstadoContrato) -> None:
    """Recorre la Línea A por el camino feliz hasta `hasta` (inclusive)."""
    for estado in _ORDEN_A:
        actual = contrato.estado
        if actual == EstadoContrato.admisibilidad_2:
            contrato.abogado_id = usuarios[Rol.legal].id
        if actual == EstadoContrato.integracion:
            contrato.administrador_id = usuarios[Rol.admin_contratos].id
            contrato.fecha_fin_vigencia = date(2030, 1, 1)

        rol = {
            EstadoContrato.aprobacion_jefatura: Rol.unidad_solicitante,
            EstadoContrato.admisibilidad_1: Rol.jefatura,
            EstadoContrato.admisibilidad_2: Rol.legal,
            EstadoContrato.elaboracion: Rol.legal,
            EstadoContrato.visacion: Rol.legal,
            EstadoContrato.firma: Rol.legal,
            EstadoContrato.integracion: Rol.legal,
            EstadoContrato.vigente: Rol.admin_contratos,
        }[estado]
        extra = {}
        if estado == EstadoContrato.visacion:
            extra = {"borrador_cargado": True}
        if estado == EstadoContrato.integracion:
            extra = {"documento_firmado": True}
        motor.transicionar_contrato(contrato, estado, usuario=usuarios[rol], extra=extra)
        if estado == hasta:
            return
