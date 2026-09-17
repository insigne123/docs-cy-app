"""Importa una planilla de contratos a la base configurada.

Uso:
    python -m scripts.importar <archivo>
donde <archivo> está en Contratos/Planillas/ (o pasa una ruta completa).
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.database import SessionLocal, crear_todo
from app.services.importador import importar_planilla_contratos
from app.services.parametros import sembrar_parametros


def main() -> None:
    if len(sys.argv) < 2:
        print("uso: python -m scripts.importar <archivo-en-Contratos/Planillas>")
        raise SystemExit(2)

    arg = sys.argv[1]
    ruta = Path(arg)
    if not ruta.exists():
        ruta = Path("Contratos/Planillas") / arg
    if not ruta.exists():
        print(f"No existe el archivo: {ruta}")
        raise SystemExit(1)

    crear_todo()
    with SessionLocal() as s:
        sembrar_parametros(s)
        s.commit()
        res = importar_planilla_contratos(s, ruta)
        s.commit()

    print(f"Creados:      {len(res.creados)}  {res.creados}")
    print(f"Actualizados: {len(res.actualizados)}  {res.actualizados}")
    print(f"Errores:      {len(res.errores)}")
    for e in res.errores:
        print(f"  [{e['hoja']} fila {e['fila']}] {e['motivo']}")
    print(f"Advertencias: {len(res.advertencias)}")
    for a in res.advertencias:
        print(f"  {a}")


if __name__ == "__main__":
    main()
