"""Genera el reporte mensual y lo guarda en reportes/.

Uso:
    python -m scripts.reporte 2026-03 xlsx
    python -m scripts.reporte 2026-03 pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.database import SessionLocal, crear_todo
from app.services.parametros import sembrar_parametros
from app.services.reportes import generar_reporte_mensual


def main() -> None:
    if len(sys.argv) < 2:
        print("uso: python -m scripts.reporte <AAAA-MM> [xlsx|pdf]")
        raise SystemExit(2)
    periodo = sys.argv[1]
    formato = sys.argv[2] if len(sys.argv) > 2 else "xlsx"
    anio, mes = (int(x) for x in periodo.split("-"))

    crear_todo()
    with SessionLocal() as s:
        sembrar_parametros(s)
        s.commit()
        contenido, nombre, _ = generar_reporte_mensual(s, anio, mes, formato)

    destino = Path("reportes")
    destino.mkdir(exist_ok=True)
    ruta = destino / nombre
    ruta.write_bytes(contenido)
    print(f"Escrito: {ruta} ({len(contenido)} bytes)")


if __name__ == "__main__":
    main()
