"""Motor de estados: aplica una transición, valida rol y precondiciones, y registra el evento."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.enums import (
    ESTADOS_CONTRATO_TERMINALES,
    ESTADOS_LICITACION_TERMINALES,
    EntidadTipo,
    EstadoContrato,
    EstadoLicitacion,
    Rol,
)
from app.models.contrato import Contrato
from app.models.evento import EventoEstado
from app.models.licitacion import Licitacion
from app.state_machine.context import ContextoTransicion
from app.state_machine.errors import (
    PrecondicionNoCumplida,
    RolNoAutorizado,
    TransicionNoPermitida,
)
from app.state_machine.transitions import (
    TRANSICIONES_CONTRATO,
    TRANSICIONES_LICITACION,
    buscar,
)

_ROLES_QUE_DESCARTAN = frozenset(r.value for r in Rol)
_TERMINALES_CONTRATO = frozenset(e.value for e in ESTADOS_CONTRATO_TERMINALES)
_TERMINALES_LICITACION = frozenset(e.value for e in ESTADOS_LICITACION_TERMINALES)


def _val(x: Any) -> str:
    return x.value if hasattr(x, "value") else str(x)


class MotorEstados:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ API pública
    def transicionar(self, entidad: Any, hacia: Any, **kwargs) -> EventoEstado:
        if isinstance(entidad, Contrato):
            return self.transicionar_contrato(entidad, hacia, **kwargs)
        if isinstance(entidad, Licitacion):
            return self.transicionar_licitacion(entidad, hacia, **kwargs)
        raise TypeError(f"Entidad no soportada: {type(entidad)!r}")

    def historial(self, entidad: Any) -> list[EventoEstado]:
        et = self._entidad_tipo(entidad)
        return (
            self.session.query(EventoEstado)
            .filter(EventoEstado.entidad_tipo == et, EventoEstado.entidad_id == entidad.id)
            .order_by(EventoEstado.fecha, EventoEstado.id)
            .all()
        )

    # ------------------------------------------------------------------ contrato
    def transicionar_contrato(
        self,
        contrato: Contrato,
        hacia: Any,
        *,
        usuario: Any,
        rol: Optional[Any] = None,
        comentario: Optional[str] = None,
        retorno_a: Optional[Any] = None,
        extra: Optional[dict] = None,
        fecha: Optional[datetime] = None,
    ) -> EventoEstado:
        estado_actual = _val(contrato.estado)
        hacia_val = _val(hacia)
        rol_val = _val(rol) if rol is not None else _val(usuario.rol)
        fecha = fecha or datetime.utcnow()
        extra = extra or {}

        if estado_actual in _TERMINALES_CONTRATO:
            raise TransicionNoPermitida(
                f"El contrato está en estado terminal '{estado_actual}'"
            )
        self._validar_estado_destino(hacia_val, EstadoContrato)

        ctx = ContextoTransicion(
            session=self.session,
            entidad=contrato,
            entidad_tipo=EntidadTipo.contrato.value,
            usuario=usuario,
            rol=rol_val,
            hacia=hacia_val,
            fecha=fecha,
            comentario=comentario,
            retorno_a=_val(retorno_a) if retorno_a is not None else None,
            extra=extra,
        )

        # --- Descarte transversal (desde cualquier estado no terminal)
        if hacia_val == EstadoContrato.descartado.value:
            return self._descartar(ctx, estado_actual, contrato_like=contrato)

        # --- Salida de 'aclaraciones': solo se puede volver al estado guardado
        if estado_actual == EstadoContrato.aclaraciones.value:
            destino_esperado = contrato.retorno_a
            if hacia_val != destino_esperado:
                raise TransicionNoPermitida(
                    "Desde 'aclaraciones' solo se puede volver a "
                    f"'{destino_esperado}', no a '{hacia_val}'"
                )

        transicion = buscar(TRANSICIONES_CONTRATO, estado_actual, hacia_val, _val(contrato.linea))
        if transicion is None:
            raise TransicionNoPermitida(
                f"No existe transición '{estado_actual}' -> '{hacia_val}' "
                f"para la línea {_val(contrato.linea)}"
            )
        if rol_val not in transicion.roles:
            raise RolNoAutorizado(
                f"El rol '{rol_val}' no puede ejecutar la transición {transicion.codigo} "
                f"('{estado_actual}' -> '{hacia_val}')"
            )
        if transicion.guard is not None:
            transicion.guard(ctx)

        # --- Aplicar
        contrato.estado = EstadoContrato(hacia_val)
        contrato.estado_desde = fecha
        if hacia_val == EstadoContrato.aclaraciones.value:
            contrato.retorno_a = transicion.set_retorno_a or ctx.retorno_a or estado_actual
        elif estado_actual == EstadoContrato.aclaraciones.value:
            contrato.retorno_a = None
        if transicion.efecto is not None:
            transicion.efecto(ctx)

        return self._registrar_evento(
            entidad_tipo=EntidadTipo.contrato.value,
            entidad_id=contrato.id,
            estado_origen=estado_actual,
            estado_destino=hacia_val,
            fecha=fecha,
            usuario_id=usuario.id,
            rol_actor=rol_val,
            comentario=comentario,
            retorno_a=contrato.retorno_a if hacia_val == EstadoContrato.aclaraciones.value else None,
        )

    # ------------------------------------------------------------------ licitación
    def transicionar_licitacion(
        self,
        licitacion: Licitacion,
        hacia: Any,
        *,
        usuario: Any,
        rol: Optional[Any] = None,
        comentario: Optional[str] = None,
        extra: Optional[dict] = None,
        fecha: Optional[datetime] = None,
    ) -> EventoEstado:
        estado_actual = _val(licitacion.estado)
        hacia_val = _val(hacia)
        rol_val = _val(rol) if rol is not None else _val(usuario.rol)
        fecha = fecha or datetime.utcnow()
        extra = extra or {}

        if estado_actual in _TERMINALES_LICITACION:
            raise TransicionNoPermitida(
                f"La licitación está en estado terminal '{estado_actual}'"
            )
        self._validar_estado_destino(hacia_val, EstadoLicitacion)

        ctx = ContextoTransicion(
            session=self.session,
            entidad=licitacion,
            entidad_tipo=EntidadTipo.licitacion.value,
            usuario=usuario,
            rol=rol_val,
            hacia=hacia_val,
            fecha=fecha,
            comentario=comentario,
            extra=extra,
        )

        if hacia_val == EstadoLicitacion.descartado.value:
            return self._descartar(ctx, estado_actual, contrato_like=None)

        transicion = buscar(TRANSICIONES_LICITACION, estado_actual, hacia_val, None)
        if transicion is None:
            raise TransicionNoPermitida(
                f"No existe transición '{estado_actual}' -> '{hacia_val}' para licitación"
            )
        if rol_val not in transicion.roles:
            raise RolNoAutorizado(
                f"El rol '{rol_val}' no puede ejecutar la transición {transicion.codigo}"
            )
        if transicion.guard is not None:
            transicion.guard(ctx)

        licitacion.estado = EstadoLicitacion(hacia_val)
        if transicion.efecto is not None:
            transicion.efecto(ctx)

        return self._registrar_evento(
            entidad_tipo=EntidadTipo.licitacion.value,
            entidad_id=licitacion.id,
            estado_origen=estado_actual,
            estado_destino=hacia_val,
            fecha=fecha,
            usuario_id=usuario.id,
            rol_actor=rol_val,
            comentario=comentario,
            retorno_a=None,
        )

    # ------------------------------------------------------------------ internos
    def _descartar(self, ctx: ContextoTransicion, estado_actual: str, contrato_like) -> EventoEstado:
        if not ctx.comentario:
            raise PrecondicionNoCumplida("El descarte exige un motivo (comentario)")
        if ctx.rol not in _ROLES_QUE_DESCARTAN:
            raise RolNoAutorizado(f"El rol '{ctx.rol}' no puede descartar el proceso")

        if contrato_like is not None:
            contrato_like.estado = EstadoContrato.descartado
            contrato_like.motivo_descarte = ctx.comentario
            contrato_like.fecha_cierre = ctx.fecha.date()
            contrato_like.retorno_a = None
            destino = EstadoContrato.descartado.value
        else:
            ctx.entidad.estado = EstadoLicitacion.descartado
            destino = EstadoLicitacion.descartado.value

        return self._registrar_evento(
            entidad_tipo=ctx.entidad_tipo,
            entidad_id=ctx.entidad.id,
            estado_origen=estado_actual,
            estado_destino=destino,
            fecha=ctx.fecha,
            usuario_id=ctx.usuario.id,
            rol_actor=ctx.rol,
            comentario=ctx.comentario,
            retorno_a=None,
        )

    def _registrar_evento(self, **kwargs) -> EventoEstado:
        evento = EventoEstado(**kwargs)
        self.session.add(evento)
        self.session.flush()
        return evento

    @staticmethod
    def _validar_estado_destino(valor: str, enum_cls) -> None:
        try:
            enum_cls(valor)
        except ValueError as exc:  # pragma: no cover - defensivo
            raise TransicionNoPermitida(f"Estado destino desconocido: '{valor}'") from exc

    @staticmethod
    def _entidad_tipo(entidad: Any) -> str:
        if isinstance(entidad, Contrato):
            return EntidadTipo.contrato.value
        if isinstance(entidad, Licitacion):
            return EntidadTipo.licitacion.value
        raise TypeError(f"Entidad no soportada: {type(entidad)!r}")
