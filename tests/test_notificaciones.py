"""Notificaciones por correo (Resend) al llegar a un estado que necesita la
acción de otro rol. Sin RESEND_API_KEY no debe hacer ninguna llamada de red."""
from __future__ import annotations

from app.enums import EstadoContrato, LineaContrato, Rol
from app.services.contratos import crear_contrato
from app.state_machine import MotorEstados
from tests._helpers import avanzar_a


def test_enviar_email_sin_api_key_no_hace_nada(monkeypatch):
    from app.config import settings
    from app.services import notificaciones

    monkeypatch.setattr(settings, "resend_api_key", "")
    llamado = {"veces": 0}
    monkeypatch.setattr(
        notificaciones.urllib.request, "urlopen",
        lambda *a, **k: llamado.__setitem__("veces", llamado["veces"] + 1),
    )
    assert notificaciones.enviar_email(["a@b.cl"], "asunto", "<p>x</p>") is False
    assert llamado["veces"] == 0


def test_notificar_transicion_contrato_envia_a_los_roles_correctos(session, usuarios, unidad, contraparte, monkeypatch):
    from app.config import settings
    from app.services import notificaciones

    monkeypatch.setattr(settings, "resend_api_key", "clave-de-prueba")
    enviados = []
    monkeypatch.setattr(
        notificaciones, "enviar_email",
        lambda destinatarios, asunto, html: enviados.append((destinatarios, asunto)) or True,
    )

    c = crear_contrato(
        session, codigo="CT-NOTIF-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    avanzar_a(MotorEstados(session), c, usuarios, EstadoContrato.aprobacion_jefatura)
    session.commit()

    notificaciones.notificar_transicion_contrato(session, c)
    assert len(enviados) == 1
    destinatarios, asunto = enviados[0]
    # aprobacion_jefatura -> ... es exclusiva de Jefatura.
    assert destinatarios == [usuarios[Rol.jefatura].email]
    assert "CT-NOTIF-1" in asunto


def test_notificar_transicion_contrato_sin_destinatarios_no_falla(session, usuarios, unidad, contraparte, monkeypatch):
    """Un contrato 'terminado'/'descartado' no tiene ningún rol que pueda
    seguir actuando -> no debe intentar enviar nada ni fallar."""
    from app.config import settings
    from app.services import notificaciones

    monkeypatch.setattr(settings, "resend_api_key", "clave-de-prueba")
    llamado = {"veces": 0}
    monkeypatch.setattr(notificaciones, "enviar_email", lambda *a, **k: llamado.__setitem__("veces", llamado["veces"] + 1))

    c = crear_contrato(
        session, codigo="CT-NOTIF-2", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    c.estado = EstadoContrato.terminado
    session.commit()

    notificaciones.notificar_transicion_contrato(session, c)
    assert llamado["veces"] == 0


def test_notificacion_no_rompe_la_transicion_si_falla(api, session, usuarios, unidad, contraparte, monkeypatch):
    """Si Resend falla (o lanza cualquier excepción), la transición del
    contrato igual debe quedar aplicada y la respuesta debe ser exitosa."""
    from app.config import settings
    from app.services import notificaciones
    from app.services.auth import hash_password

    monkeypatch.setattr(settings, "resend_api_key", "clave-de-prueba")
    def _falla(*a, **k):
        raise RuntimeError("Resend caído")
    monkeypatch.setattr(notificaciones, "enviar_email", _falla)

    c = crear_contrato(
        session, codigo="CT-NOTIF-3", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    solicitante = usuarios[Rol.unidad_solicitante]
    solicitante.password_hash = hash_password("clave12345")
    session.commit()
    api.post("/login", data={"email": solicitante.email, "password": "clave12345"})

    r = api.post(f"/panel/contratos/{c.id}/transicion", data={"hacia": "aprobacion_jefatura"}, follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(c)
    assert c.estado.value == "aprobacion_jefatura"
