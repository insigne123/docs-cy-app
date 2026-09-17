"""Genera Contratos/Planillas/ejemplo.xlsx con datos ficticios para probar el importador.

Uso:
    python -m scripts.crear_planilla_ejemplo
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

DESTINO = Path("Contratos/Planillas/ejemplo.xlsx")

CONTRATOS = [
    # codigo_externo, linea, objeto, categoria, unidad, solicitante, contraparte, rut, cont_email,
    # abogado, admin, formato, lic_codigo, estado, monto, moneda, req_gar, f_ingreso, f_aprob,
    # f_adm, f_vis, f_firma, f_integ, f_ini_vig, f_fin_vig, vig_indef, renov, aviso, causales, archivo, obs
    ["SC-1001", "A", "Servicio de aseo oficinas", "servicio", "Operaciones", "jperez@empresa.cl",
     "Aseos del Sur SpA", "76.111.111-1", "contacto@aseosdelsur.cl", "mlopez@empresa.cl",
     "rgomez@empresa.cl", "", "", "vigente", "18500000", "CLP", "no",
     "2025-03-04", "2025-03-06", "2025-03-12", "2025-03-20", "2025-03-25", "2025-03-28",
     "2025-04-01", "2026-03-31", "no", "automatica", "60", "Incumplimiento grave", "", "Carga inicial"],
    ["SC-1002", "A", "Licencia software gestión", "licencia", "TI", "avega@empresa.cl",
     "Cloud Andes SpA", "77.222.222-2", "", "mlopez@empresa.cl", "rgomez@empresa.cl", "", "",
     "vigente", "9600000", "CLP", "no", "2025-05-10", "2025-05-11", "2025-05-12", "2025-05-13",
     "2025-05-14", "2025-05-15", "2025-05-15", "", "si", "sin_renovacion", "30", "", "", ""],
    ["SC-1003", "A", "Mantención ascensores", "servicio", "Infraestructura", "jperez@empresa.cl",
     "Elevacon Ltda", "78.333.333-3", "", "mlopez@empresa.cl", "rgomez@empresa.cl", "", "",
     "elaboracion", "42000000", "CLP", "si", "2026-01-15", "2026-01-17", "2026-01-22", "", "",
     "", "", "", "no", "con_aviso", "90", "", "", "En redacción"],
]

GARANTIAS = [
    ["SC-1001", "fiel_cumplimiento", "boleta_bancaria", "Banco Estado", "0012345", "1850000",
     "CLP", "2025-03-24", "2026-04-30", "vigente", "Garantiza fiel cumplimiento"],
    ["SC-1003", "fiel_cumplimiento", "poliza_seguro", "Aseguradora XYZ", "P-9987", "4200000",
     "CLP", "2026-01-20", "2027-02-28", "vigente", ""],
]

HITOS = [
    ["SC-1001", "renovacion", "Aviso de renovación", "2026-01-31", "", "pendiente",
     "rgomez@empresa.cl", ""],
    ["SC-1001", "pago", "Pago mensualidad enero", "2025-05-05", "2025-05-05", "cumplido", "", ""],
]

HDR_CONTRATOS = [
    "codigo_externo", "linea", "objeto", "categoria", "unidad_solicitante", "solicitante_email",
    "contraparte_razon_social", "contraparte_rut", "contraparte_contacto_email", "abogado_email",
    "administrador_email", "formato_estandar", "licitacion_codigo", "estado_actual", "monto",
    "moneda", "requiere_garantia", "fecha_ingreso", "fecha_aprobacion_jefatura", "fecha_admisibilidad",
    "fecha_visacion", "fecha_firma", "fecha_integracion", "fecha_inicio_vigencia", "fecha_fin_vigencia",
    "vigencia_indefinida", "tipo_renovacion", "aviso_previo_dias", "causales_termino",
    "archivo_contrato", "observaciones",
]
HDR_GARANTIAS = [
    "contrato_codigo_externo", "tipo", "instrumento", "emisor", "numero", "monto", "moneda",
    "fecha_emision", "fecha_vencimiento", "estado", "glosa",
]
HDR_HITOS = [
    "contrato_codigo_externo", "tipo", "nombre", "fecha_planificada", "fecha_real", "estado",
    "responsable_email", "notas",
]


def _hoja(wb, titulo, encabezado, filas):
    ws = wb.create_sheet(titulo)
    ws.append(encabezado)
    for f in filas:
        ws.append(f)


def main() -> None:
    wb = Workbook()
    wb.remove(wb.active)
    _hoja(wb, "Contratos", HDR_CONTRATOS, CONTRATOS)
    _hoja(wb, "Garantias", HDR_GARANTIAS, GARANTIAS)
    _hoja(wb, "Hitos", HDR_HITOS, HITOS)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    wb.save(DESTINO)
    print(f"Escrito: {DESTINO}")


if __name__ == "__main__":
    main()
