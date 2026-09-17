"""Crea el esquema de base de datos (Etapa 1) y siembra los parámetros por defecto.

Uso:
    python -m scripts.init_db
"""
from __future__ import annotations

from app.database import SessionLocal, crear_todo
from app.services.parametros import sembrar_parametros


def main() -> None:
    crear_todo()
    with SessionLocal() as s:
        sembrar_parametros(s)
        s.commit()
    print("Esquema creado y parámetros sembrados.")


if __name__ == "__main__":
    main()
