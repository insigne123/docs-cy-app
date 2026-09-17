"""Línea C — Licitaciones (Fase I Pre-Adjudicación + Fase II Formalización)."""
from __future__ import annotations

from datetime import date

import pytest

from app.enums import (
    EstadoContrato,
    EstadoLicitacion,
    GarantiaEstado,
    GarantiaInstrumento,
    GarantiaTipo,
    LicitacionFase,
    LicitacionResultado,
    LineaContrato,
    Moneda,
    Rol,
)
from app.models.contrato import Garantia
from app.services.licitaciones import adjudicar_licitacion, crear_licitacion
from app.state_machine import MotorEstados, PrecondicionNoCumplida


def _fase_i_hasta_evaluacion(session, motor, usuarios, unidad):
    lic = crear_licitacion(
        session,
        codigo="LIC-2026-0001",
        objeto="Mantención de flota",
        unidad_solicitante=unidad,
        solicitante=usuarios[Rol.admin_licitaciones],
        moneda=Moneda.CLP,
    )
    session.commit()
    motor.transicionar_licitacion(lic, EstadoLicitacion.examen_admisibilidad, usuario=usuarios[Rol.admin_licitaciones])
    motor.transicionar_licitacion(lic, EstadoLicitacion.revision_bases, usuario=usuarios[Rol.legal])
    motor.transicionar_licitacion(
        lic, EstadoLicitacion.preparacion_oferta, usuario=usuarios[Rol.legal],
        extra={"informe_riesgos_ok": True},
    )
    motor.transicionar_licitacion(
        lic, EstadoLicitacion.presentacion_oferta, usuario=usuarios[Rol.tecnica],
        extra={"oferta_tecnica_ok": True, "oferta_economica_ok": True},
    )
    motor.transicionar_licitacion(lic, EstadoLicitacion.evaluacion_resultado, usuario=usuarios[Rol.admin_licitaciones])
    return lic


def test_licitacion_completa_adjudicada_y_formalizada(session, usuarios, unidad):
    motor = MotorEstados(session)
    lic = _fase_i_hasta_evaluacion(session, motor, usuarios, unidad)

    contrato = adjudicar_licitacion(
        session, lic, usuario=usuarios[Rol.admin_licitaciones], codigo_contrato="CT-2026-0003"
    )
    session.commit()

    assert lic.estado == EstadoLicitacion.adjudicada
    assert lic.resultado == LicitacionResultado.adjudicado
    assert lic.fase == LicitacionFase.formalizacion
    assert lic.contrato_id == contrato.id
    assert contrato.linea == LineaContrato.C_licitacion
    assert contrato.licitacion_id == lic.id
    assert contrato.estado == EstadoContrato.formalizacion_ajuste

    # Gate 1 -> Gate 2
    motor.transicionar_contrato(
        contrato, EstadoContrato.constitucion_garantias, usuario=usuarios[Rol.legal],
        extra={"coherente_con_oferta": True},
    )
    # Gate 2 -> Gate 3 SIN garantía: se rechaza
    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(contrato, EstadoContrato.firma, usuario=usuarios[Rol.financiera])

    session.add(
        Garantia(
            entidad_tipo="contrato",
            entidad_id=contrato.id,
            tipo=GarantiaTipo.fiel_cumplimiento,
            instrumento=GarantiaInstrumento.boleta_bancaria,
            monto=5_000_000,
            moneda=Moneda.CLP,
            fecha_emision=date(2026, 1, 1),
            fecha_vencimiento=date(2027, 12, 1),
            estado=GarantiaEstado.vigente,
        )
    )
    session.flush()

    motor.transicionar_contrato(contrato, EstadoContrato.firma, usuario=usuarios[Rol.financiera])
    motor.transicionar_contrato(
        contrato, EstadoContrato.integracion, usuario=usuarios[Rol.legal],
        extra={"documento_firmado": True},
    )
    contrato.administrador_id = usuarios[Rol.admin_contratos].id
    contrato.fecha_fin_vigencia = date(2028, 1, 1)
    motor.transicionar_contrato(contrato, EstadoContrato.vigente, usuario=usuarios[Rol.admin_contratos])
    session.commit()

    assert contrato.estado == EstadoContrato.vigente
    destinos = [e.estado_destino for e in motor.historial(contrato)]
    assert destinos == [
        "formalizacion_ajuste",
        "constitucion_garantias",
        "firma",
        "integracion",
        "vigente",
    ]


def test_licitacion_no_adjudicada_exige_analisis_interno(session, usuarios, unidad):
    motor = MotorEstados(session)
    lic = _fase_i_hasta_evaluacion(session, motor, usuarios, unidad)

    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_licitacion(
            lic, EstadoLicitacion.no_adjudicada, usuario=usuarios[Rol.admin_licitaciones]
        )

    motor.transicionar_licitacion(
        lic, EstadoLicitacion.no_adjudicada, usuario=usuarios[Rol.admin_licitaciones],
        extra={"analisis_interno": "Precio fuera de mercado; se ajustará la estrategia."},
    )
    session.commit()
    assert lic.estado == EstadoLicitacion.no_adjudicada
    assert lic.resultado == LicitacionResultado.no_adjudicado
    assert lic.analisis_interno


def test_licitacion_preparacion_sin_informe_riesgos_se_rechaza(session, usuarios, unidad):
    motor = MotorEstados(session)
    lic = crear_licitacion(
        session,
        codigo="LIC-2026-0002",
        objeto="Suministro",
        unidad_solicitante=unidad,
        solicitante=usuarios[Rol.admin_licitaciones],
    )
    session.commit()
    motor.transicionar_licitacion(lic, EstadoLicitacion.examen_admisibilidad, usuario=usuarios[Rol.admin_licitaciones])
    motor.transicionar_licitacion(lic, EstadoLicitacion.revision_bases, usuario=usuarios[Rol.tecnica])
    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_licitacion(
            lic, EstadoLicitacion.preparacion_oferta, usuario=usuarios[Rol.legal]
        )
