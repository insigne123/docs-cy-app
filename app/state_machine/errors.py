"""Errores del motor de estados."""
from __future__ import annotations


class ErrorTransicion(Exception):
    """Base de todos los errores del motor de estados."""


class TransicionNoPermitida(ErrorTransicion):
    """No existe una transición válida entre los estados indicados para esa línea."""


class RolNoAutorizado(ErrorTransicion):
    """El rol del usuario no puede ejecutar esta transición."""


class PrecondicionNoCumplida(ErrorTransicion):
    """La transición existe pero no se cumple una de sus precondiciones (guard)."""
