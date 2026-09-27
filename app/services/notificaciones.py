"""Notificaciones por correo (Resend) cuando un contrato o licitación llega a
un estado que necesita la acción de otro rol — la misma lógica que ya usa
Mis tareas para decidir "a quién le toca actuar ahora".

Sin RESEND_API_KEY configurada (vacío por defecto) esto no hace nada, ni
siquiera abre una conexión de red: así queda desactivado por defecto en
desarrollo y en las pruebas, sin necesitar mocks.

Cualquier error de red o de la API de Resend se registra en el log pero
nunca interrumpe la transición que lo disparó — es un aviso de mejor
esfuerzo, no una parte crítica del flujo.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.contrato import Contrato
from app.models.core import Usuario
from app.models.licitacion import Licitacion
from app.services.tareas import roles_que_pueden_actuar_contrato, roles_que_pueden_actuar_licitacion

log = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


def enviar_email(destinatarios: list[str], asunto: str, cuerpo_html: str) -> bool:
    if not settings.resend_api_key or not destinatarios:
        return False
    payload = json.dumps({
        "from": settings.resend_from,
        "to": destinatarios,
        "subject": asunto,
        "html": cuerpo_html,
    }).encode("utf-8")
    req = urllib.request.Request(
        _RESEND_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001 - nunca debe romper la transición que lo disparó
        log.warning("no se pudo enviar la notificación por correo: %s", exc)
        return False


def _emails_para_roles(session: Session, roles: frozenset[str]) -> list[str]:
    if not roles:
        return []
    usuarios = session.scalars(
        select(Usuario).where(Usuario.activo.is_(True), Usuario.rol.in_(roles))
    )
    return [u.email for u in usuarios if u.email]


def notificar_transicion_contrato(session: Session, contrato: Contrato) -> None:
    try:
        roles = roles_que_pueden_actuar_contrato(contrato.estado.value, contrato.linea.value)
        destinatarios = _emails_para_roles(session, roles)
        if not destinatarios:
            return
        url = f"{settings.app_base_url}/panel/contratos/{contrato.id}"
        estado_legible = contrato.estado.value.replace("_", " ")
        enviar_email(
            destinatarios,
            f"Acción requerida: {contrato.codigo} está en '{estado_legible}'",
            f"<p>El contrato <strong>{contrato.codigo}</strong> ({contrato.objeto}) "
            f"está esperando tu acción en el estado <strong>{estado_legible}</strong>.</p>"
            f'<p><a href="{url}">Ver ficha del contrato</a></p>',
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("no se pudo notificar la transición del contrato %s: %s", contrato.id, exc)


def notificar_transicion_licitacion(session: Session, licitacion: Licitacion) -> None:
    try:
        roles = roles_que_pueden_actuar_licitacion(licitacion.estado.value)
        destinatarios = _emails_para_roles(session, roles)
        if not destinatarios:
            return
        url = f"{settings.app_base_url}/panel/licitaciones/{licitacion.id}"
        estado_legible = licitacion.estado.value.replace("_", " ")
        enviar_email(
            destinatarios,
            f"Acción requerida: {licitacion.codigo} está en '{estado_legible}'",
            f"<p>La licitación <strong>{licitacion.codigo}</strong> ({licitacion.objeto}) "
            f"está esperando tu acción en el estado <strong>{estado_legible}</strong>.</p>"
            f'<p><a href="{url}">Ver ficha de la licitación</a></p>',
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("no se pudo notificar la transición de la licitación %s: %s", licitacion.id, exc)
