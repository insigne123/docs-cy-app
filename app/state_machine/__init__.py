"""Motor de estados del sistema de contratos y licitaciones."""
from app.state_machine.engine import MotorEstados
from app.state_machine.errors import (
    ErrorTransicion,
    PrecondicionNoCumplida,
    RolNoAutorizado,
    TransicionNoPermitida,
)

__all__ = [
    "MotorEstados",
    "ErrorTransicion",
    "TransicionNoPermitida",
    "RolNoAutorizado",
    "PrecondicionNoCumplida",
]
