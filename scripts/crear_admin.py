"""Crea (o actualiza la clave de) un usuario administrador, sin pasar por la API.

Necesario para el primer ingreso cuando AUTH_REQUIRED=true: todos los endpoints de
escritura exigen token, así que el primer usuario con contraseña se crea directo en la
base de datos.

Requiere que el esquema ya exista (`alembic upgrade head` ya ejecutado en esa base;
en el despliegue eso ocurre automáticamente antes de levantar el servidor).

Uso:
    python -m scripts.crear_admin admin@empresa.cl "Clave Segura 123" "Nombre Admin"

En Railway/Render, ejecutar una vez contra la base de producción:
    railway run python -m scripts.crear_admin admin@empresa.cl "clave" "Admin"
    (Render: usar el Shell del servicio, o un "One-Off Job")
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.enums import Rol
from app.models.core import Usuario
from app.services.auth import hash_password


def main() -> None:
    if len(sys.argv) < 3:
        print('uso: python -m scripts.crear_admin <email> "<clave>" ["Nombre"] [rol]')
        raise SystemExit(2)
    email = sys.argv[1].strip().lower()
    clave = sys.argv[2]
    nombre = sys.argv[3] if len(sys.argv) > 3 else email.split("@")[0]
    rol = Rol(sys.argv[4]) if len(sys.argv) > 4 else Rol.admin_sistema

    with SessionLocal() as s:
        usuario = s.scalars(select(Usuario).where(Usuario.email == email)).first()
        if usuario is None:
            usuario = Usuario(nombre=nombre, email=email, rol=rol, activo=True)
            s.add(usuario)
            accion = "creado"
        else:
            accion = "actualizado (clave renovada)"
        usuario.password_hash = hash_password(clave)
        usuario.activo = True
        s.commit()
        print(f"Usuario {accion}: {usuario.email} (id={usuario.id}, rol={usuario.rol.value})")


if __name__ == "__main__":
    main()
