"""Respaldo y restauración de la base de datos.

Uso:
    python -m scripts.respaldo                 # crea respaldos/backup_AAAAMMDD_HHMMSS.db
    python -m scripts.respaldo restaurar <archivo>   # restaura desde un respaldo (SQLite)

Sólo cubre SQLite (uso local). En PostgreSQL usar pg_dump / pg_restore.
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

from app.config import settings


def _ruta_sqlite() -> Path:
    url = settings.database_url
    if not url.startswith("sqlite"):
        print(f"DATABASE_URL no es SQLite ({url}). Usa pg_dump para PostgreSQL.")
        raise SystemExit(2)
    return Path(url.split("///", 1)[1])


def crear() -> None:
    origen = _ruta_sqlite()
    if not origen.exists():
        print(f"No existe la base: {origen}")
        raise SystemExit(1)
    carpeta = Path("respaldos")
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / f"backup_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(origen, destino)
    print(f"Respaldo creado: {destino}")


def restaurar(archivo: str) -> None:
    origen = Path(archivo)
    if not origen.exists():
        print(f"No existe el respaldo: {origen}")
        raise SystemExit(1)
    destino = _ruta_sqlite()
    if destino.exists():
        previo = destino.with_suffix(destino.suffix + ".antes_de_restaurar")
        shutil.copy2(destino, previo)
        print(f"Copia de seguridad de la base actual: {previo}")
    shutil.copy2(origen, destino)
    print(f"Base restaurada desde {origen} -> {destino}")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "restaurar":
        restaurar(sys.argv[2])
    else:
        crear()


if __name__ == "__main__":
    main()
