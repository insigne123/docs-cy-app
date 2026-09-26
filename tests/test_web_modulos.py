"""Módulos web de operación: nueva solicitud, edición, garantías y avance de flujo."""
from __future__ import annotations

from app.enums import Rol
from app.services.auth import hash_password


def _login(api, session, usuarios, rol=Rol.unidad_solicitante, password="clave12345"):
    u = usuarios[rol]
    u.password_hash = hash_password(password)
    session.commit()
    r = api.post("/login", data={"email": u.email, "password": password})
    assert r.status_code in (303, 200)
    return u


def test_nuevo_contrato_requiere_login(api):
    r = api.get("/panel/contratos/nuevo", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login")


def test_crear_contrato_flujo_regular(api, session, usuarios, unidad, contraparte):
    _login(api, session, usuarios)
    r = api.post(
        "/panel/contratos/nuevo",
        data={
            "linea": "A_regular",
            "objeto": "Servicio de prueba",
            "unidad_solicitante_id": str(unidad.id),
            "contraparte_id": str(contraparte.id),
            "monto": "1000000",
            "moneda": "CLP",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/panel/contratos/" in r.headers["location"]
    detalle = api.get(r.headers["location"])
    assert detalle.status_code == 200
    assert "Servicio de prueba" in detalle.text
    assert "Flujo Regular" in detalle.text


def test_crear_autogestionado_sin_formato_muestra_error(api, session, usuarios, unidad, contraparte):
    _login(api, session, usuarios)
    r = api.post(
        "/panel/contratos/nuevo",
        data={
            "linea": "B_autogestionado",
            "objeto": "NDA",
            "unidad_solicitante_id": str(unidad.id),
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "error=" in r.headers["location"]


def test_editar_contrato(api, session, usuarios, unidad, contraparte):
    u = _login(api, session, usuarios, rol=Rol.admin_contratos)
    from app.enums import LineaContrato, Moneda
    from app.services.contratos import crear_contrato

    c = crear_contrato(
        session, codigo="CT-WEB-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=u, contraparte=contraparte,
    )
    session.commit()

    r = api.post(
        f"/panel/contratos/{c.id}/editar",
        data={
            "administrador_id": str(u.id),
            "monto": "500000",
            "moneda": "CLP",
            "vigencia_indefinida": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    session.refresh(c)
    assert c.administrador_id == u.id
    assert c.vigencia_indefinida is True


def test_agregar_garantia_y_transicion(api, session, usuarios, unidad, contraparte):
    u = _login(api, session, usuarios, rol=Rol.legal)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato
    from tests._helpers import avanzar_a
    from app.enums import EstadoContrato
    from app.state_machine import MotorEstados

    c = crear_contrato(
        session, codigo="CT-WEB-2", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante],
        contraparte=contraparte, requiere_garantia=True,
    )
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.visacion)
    session.commit()

    # Firma sin garantía -> error visible, no un 500
    r = api.post(f"/panel/contratos/{c.id}/transicion", data={"hacia": "firma"}, follow_redirects=False)
    assert r.status_code == 303
    assert "error=" in r.headers["location"]

    # Constituir la garantía es atribución exclusiva de Financiera (ver docs/CLAUDE.md).
    _login(api, session, usuarios, rol=Rol.financiera)
    r = api.post(
        f"/panel/contratos/{c.id}/garantias",
        data={
            "tipo": "fiel_cumplimiento", "instrumento": "boleta_bancaria",
            "monto": "100000", "moneda": "CLP",
            "fecha_emision": "2026-01-01", "fecha_vencimiento": "2027-01-01",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    _login(api, session, usuarios, rol=Rol.legal)
    r = api.post(f"/panel/contratos/{c.id}/transicion", data={"hacia": "firma"}, follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(c)
    assert c.estado.value == "firma"


def test_agregar_hito_y_marcar_cumplido(api, session, usuarios, unidad, contraparte):
    u = _login(api, session, usuarios, rol=Rol.admin_contratos)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato

    c = crear_contrato(
        session, codigo="CT-WEB-4", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()

    r = api.post(
        f"/panel/contratos/{c.id}/hitos",
        data={"tipo": "entregable", "nombre": "Entrega parcial", "fecha_planificada": "2026-12-01"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    from sqlalchemy import select
    from app.models.contrato import Hito
    hito = session.scalars(select(Hito).where(Hito.contrato_id == c.id)).first()
    assert hito is not None and hito.estado.value == "pendiente"

    r = api.post(
        f"/panel/contratos/{c.id}/hitos/{hito.id}/estado",
        data={"estado": "cumplido"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(hito)
    assert hito.estado.value == "cumplido"
    assert hito.fecha_real is not None


def test_agregar_multa_y_cambiar_estado(api, session, usuarios, unidad, contraparte):
    _login(api, session, usuarios, rol=Rol.financiera)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato

    c = crear_contrato(
        session, codigo="CT-WEB-5", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()

    r = api.post(
        f"/panel/contratos/{c.id}/multas",
        data={"descripcion": "Atraso en entrega", "monto": "50000", "moneda": "CLP", "fecha_aplicacion": "2026-11-01"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    from sqlalchemy import select
    from app.models.contrato import Multa
    multa = session.scalars(select(Multa).where(Multa.contrato_id == c.id)).first()
    assert multa is not None and multa.estado.value == "propuesta"

    r = api.post(
        f"/panel/contratos/{c.id}/multas/{multa.id}/estado",
        data={"estado": "aplicada"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(multa)
    assert multa.estado.value == "aplicada"


def test_listado_contratos_muestra_todos_los_estados(api, session, usuarios, cartera):
    _login(api, session, usuarios, rol=Rol.admin_contratos)
    r = api.get("/panel/contratos")
    assert r.status_code == 200
    texto = r.text
    for codigo in ("C-VIG", "C-PORVENCER", "C-VENCIDO", "C-RENOV", "C-TRAMITE"):
        assert codigo in texto


def test_listado_contratos_filtra_por_estado(api, session, usuarios, cartera):
    _login(api, session, usuarios, rol=Rol.admin_contratos)
    r = api.get("/panel/contratos?estado=vigente")
    assert r.status_code == 200
    assert "C-TRAMITE" not in r.text
    assert "C-VIG" in r.text


def test_exportar_listado_contratos_xlsx(api, session, usuarios, cartera):
    import io
    from openpyxl import load_workbook

    _login(api, session, usuarios, rol=Rol.admin_contratos)
    r = api.get("/panel/contratos/exportar")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb.active
    codigos = {row[0].value for row in ws.iter_rows(min_row=2)}
    for codigo in ("C-VIG", "C-PORVENCER", "C-VENCIDO", "C-RENOV", "C-TRAMITE"):
        assert codigo in codigos

    # Respeta los mismos filtros que el listado en pantalla.
    r = api.get("/panel/contratos/exportar?estado=vigente")
    wb = load_workbook(io.BytesIO(r.content))
    codigos = {row[0].value for row in wb.active.iter_rows(min_row=2)}
    assert "C-TRAMITE" not in codigos
    assert "C-VIG" in codigos


def test_exportar_listado_bloqueado_para_unidad_solicitante(api, session, usuarios, cartera):
    _login(api, session, usuarios, rol=Rol.unidad_solicitante)
    r = api.get("/panel/contratos/exportar", follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]


def test_vigencias_lista_ordenada_por_urgencia(api, session, usuarios, cartera):
    _login(api, session, usuarios, rol=Rol.admin_contratos)
    r = api.get("/panel/vigencias")
    assert r.status_code == 200
    texto = r.text
    # El vencido debe listarse antes que el vigente sin urgencia (orden por días).
    assert texto.index("C-VENCIDO") < texto.index("C-VIG")
    assert "C-TRAMITE" not in texto  # no está 'vigente', no pertenece a este módulo


def test_renovar_contrato_desde_vigencias(api, session, usuarios, cartera):
    _login(api, session, usuarios, rol=Rol.admin_contratos)
    cid = cartera["PORVENCER"]
    r = api.post(
        f"/panel/contratos/{cid}/transicion",
        data={"hacia": "vigente", "nueva_fecha_fin": "2030-01-01"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    from app.models.contrato import Contrato
    c = session.get(Contrato, cid)
    session.refresh(c)
    assert c.fecha_fin_vigencia.isoformat() == "2030-01-01"
    assert c.estado.value == "vigente"


def test_terminar_contrato_desde_vigencias(api, session, usuarios, cartera):
    _login(api, session, usuarios, rol=Rol.admin_contratos)
    cid = cartera["VENCIDO"]
    r = api.post(
        f"/panel/contratos/{cid}/transicion",
        data={"hacia": "terminado", "comentario": "Contrato vencido sin renovación"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    from app.models.contrato import Contrato
    c = session.get(Contrato, cid)
    session.refresh(c)
    assert c.estado.value == "terminado"


def test_crear_unidad_desde_catalogos(api, session, usuarios):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.post(
        "/panel/catalogos/unidades",
        data={"nombre": "Compras", "tipo": "interna"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    from sqlalchemy import select
    from app.models.core import Unidad
    u = session.scalars(select(Unidad).where(Unidad.nombre == "Compras")).first()
    assert u is not None and u.tipo.value == "interna"

    # Ahora debe aparecer en el combo de "Nueva solicitud".
    r = api.get("/panel/contratos/nuevo")
    assert "Compras" in r.text


def test_crear_unidad_duplicada_muestra_error(api, session, usuarios, unidad):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.post(
        "/panel/catalogos/unidades",
        data={"nombre": unidad.nombre, "tipo": "solicitante"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "error=" in r.headers["location"]


def test_crear_contraparte_desde_catalogos(api, session, usuarios):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.post(
        "/panel/catalogos/contrapartes",
        data={"razon_social": "Logística Andina Ltda.", "tipo": "proveedor", "rut": "76.111.222-3"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    r = api.get("/panel/catalogos")
    assert "Logística Andina Ltda." in r.text


def test_crear_formato_desde_administracion(api, session, usuarios):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.post(
        "/panel/catalogos/formatos",
        data={
            "nombre": "NDA v2", "version": "2", "aprobado_por": "Fiscalia",
            "fecha_aprobacion": "2026-01-01", "campos_variables": "contraparte, fecha",
            "ruta_plantilla": "formatos/nda_v2.docx", "vigente": "1",
        },
        files={"plantilla_archivo": ("nda_v2.docx", b"contenido de prueba del formato", "application/octet-stream")},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    r = api.get("/panel/contratos/nuevo")
    assert "NDA v2" in r.text

    from hashlib import sha256
    from sqlalchemy import select
    from app.models.core import FormatoEstandar
    formato = session.scalars(select(FormatoEstandar).where(FormatoEstandar.nombre == "NDA v2")).first()
    assert formato.checksum_base == sha256(b"contenido de prueba del formato").hexdigest()
    assert formato.contenido == b"contenido de prueba del formato"
    assert formato.nombre_archivo == "nda_v2.docx"

    # El botón de "Previsualizar" solo aparece cuando hay contenido guardado.
    r = api.get("/panel/catalogos")
    assert f"/panel/catalogos/formatos/{formato.id}/plantilla" in r.text

    r = api.get(f"/panel/catalogos/formatos/{formato.id}/plantilla")
    assert r.status_code == 200
    assert r.content == b"contenido de prueba del formato"
    assert "inline" in r.headers["content-disposition"]


def test_previsualizar_formato_sin_contenido_da_404(api, session, usuarios, formato):
    """Los formatos creados antes de esta funcionalidad no tienen contenido
    guardado (solo el checksum) — se informa con un 404 claro en vez de servir
    un archivo vacío."""
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.get(f"/panel/catalogos/formatos/{formato.id}/plantilla")
    assert r.status_code == 404

    r = api.get("/panel/catalogos")
    assert f"/panel/catalogos/formatos/{formato.id}/plantilla" not in r.text


def test_crear_usuario_desde_administracion(api, session, usuarios, unidad):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.post(
        "/panel/catalogos/usuarios",
        data={
            "nombre": "Nueva Persona", "email": "Nueva.Persona@Empresa.cl",
            "rol": "legal", "unidad_id": str(unidad.id), "password": "clave12345",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]

    from sqlalchemy import select
    from app.models.core import Usuario
    u = session.scalars(select(Usuario).where(Usuario.email == "nueva.persona@empresa.cl")).first()
    assert u is not None and u.rol.value == "legal" and u.password_hash is not None

    # El nuevo usuario ya puede iniciar sesión.
    r2 = api.post("/login", data={"email": "nueva.persona@empresa.cl", "password": "clave12345"}, follow_redirects=False)
    assert r2.status_code == 303 and r2.headers["location"] == "/panel"


def test_crear_usuario_email_duplicado_muestra_error(api, session, usuarios):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    existente = usuarios[Rol.legal]
    r = api.post(
        "/panel/catalogos/usuarios",
        data={"nombre": "Otro", "email": existente.email, "rol": "legal"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "error=" in r.headers["location"]


def test_boton_cerrar_sesion_visible_tras_login(api, session, usuarios):
    u = _login(api, session, usuarios, rol=Rol.admin_contratos)
    r = api.get("/panel")
    assert r.status_code == 200
    assert 'href="/logout"' in r.text
    assert u.nombre in r.text

    r = api.get("/logout", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"

    r = api.get("/panel/contratos/nuevo", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


def test_rol_no_autorizado_no_puede_crear_solicitud(api, session, usuarios, unidad, contraparte):
    """Solo Unidad Solicitante (y admin_sistema) ingresa solicitudes."""
    _login(api, session, usuarios, rol=Rol.financiera)
    r = api.post(
        "/panel/contratos/nuevo",
        data={
            "linea": "A_regular", "objeto": "x",
            "unidad_solicitante_id": str(unidad.id), "contraparte_id": str(contraparte.id),
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "error=" in r.headers["location"]
    assert "financiera" in r.headers["location"]

    r = api.get("/panel/contratos/nuevo", follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]


def test_rol_no_autorizado_no_puede_agregar_garantia(api, session, usuarios, unidad, contraparte):
    """Constituir garantías es facultad exclusiva de Financiera."""
    u = _login(api, session, usuarios, rol=Rol.tecnica)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato

    c = crear_contrato(
        session, codigo="CT-ROL-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    r = api.post(
        f"/panel/contratos/{c.id}/garantias",
        data={
            "tipo": "fiel_cumplimiento", "instrumento": "boleta_bancaria",
            "monto": "100000", "moneda": "CLP",
            "fecha_emision": "2026-01-01", "fecha_vencimiento": "2027-01-01",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303 and "error=" in r.headers["location"]
    from sqlalchemy import select
    from app.models.contrato import Garantia
    assert session.scalars(select(Garantia)).first() is None


def test_rol_no_autorizado_no_puede_crear_usuario(api, session, usuarios):
    """Crear usuarios (con contraseña) es exclusivo de admin_sistema, para evitar
    escalamiento de privilegios desde cualquier otro rol."""
    _login(api, session, usuarios, rol=Rol.legal)
    r = api.post(
        "/panel/catalogos/usuarios",
        data={"nombre": "Intruso", "email": "intruso@empresa.cl", "rol": "admin_sistema"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "error=" in r.headers["location"]
    from sqlalchemy import select
    from app.models.core import Usuario
    assert session.scalars(select(Usuario).where(Usuario.email == "intruso@empresa.cl")).first() is None


def test_admin_sistema_puede_todo(api, session, usuarios, unidad, contraparte):
    """admin_sistema es el superusuario tecnico de arranque (no un rol de negocio
    documentado) y puede ejecutar cualquier accion restringida por rol."""
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato

    c = crear_contrato(
        session, codigo="CT-ROL-2", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    r = api.post(
        f"/panel/contratos/{c.id}/garantias",
        data={
            "tipo": "fiel_cumplimiento", "instrumento": "boleta_bancaria",
            "monto": "100000", "moneda": "CLP",
            "fecha_emision": "2026-01-01", "fecha_vencimiento": "2027-01-01",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]


def test_editar_y_eliminar_unidad(api, session, usuarios, unidad):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.post(
        f"/panel/catalogos/unidades/{unidad.id}/editar",
        data={"nombre": "Operaciones Renombrada", "tipo": "interna", "activo": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(unidad)
    assert unidad.nombre == "Operaciones Renombrada" and unidad.tipo.value == "interna"

    # "Eliminar" desactiva, no borra (la unidad puede estar en uso).
    r = api.post(f"/panel/catalogos/unidades/{unidad.id}/eliminar", follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(unidad)
    assert unidad.activo is False

    # Una vez inactiva, ya no aparece en el combo de "Nueva solicitud"...
    r = api.get("/panel/contratos/nuevo")
    assert "Operaciones Renombrada" not in r.text
    # ...pero sigue visible en el propio listado de Administración para poder reactivarla.
    r = api.get("/panel/catalogos")
    assert "Operaciones Renombrada" in r.text


def test_editar_y_eliminar_contraparte(api, session, usuarios, contraparte):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.post(
        f"/panel/catalogos/contrapartes/{contraparte.id}/editar",
        data={"razon_social": "Aseos del Sur Renombrada", "tipo": "proveedor"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(contraparte)
    assert contraparte.razon_social == "Aseos del Sur Renombrada"

    r = api.post(f"/panel/catalogos/contrapartes/{contraparte.id}/eliminar", follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    from sqlalchemy import select
    from app.models.core import Contraparte
    assert session.scalars(select(Contraparte).where(Contraparte.id == contraparte.id)).first() is None


def test_no_se_puede_eliminar_contraparte_en_uso(api, session, usuarios, unidad, contraparte):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato

    crear_contrato(
        session, codigo="CT-USO-1", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()
    r = api.post(f"/panel/catalogos/contrapartes/{contraparte.id}/eliminar", follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]
    from sqlalchemy import select
    from app.models.core import Contraparte
    assert session.scalars(select(Contraparte).where(Contraparte.id == contraparte.id)).first() is not None


def test_editar_y_eliminar_formato(api, session, usuarios, formato):
    _login(api, session, usuarios, rol=Rol.admin_sistema)
    r = api.post(
        f"/panel/catalogos/formatos/{formato.id}/editar",
        data={
            "nombre": "NDA estandar v2", "version": str(formato.version), "aprobado_por": "Fiscalia",
            "fecha_aprobacion": "2026-01-01", "ruta_plantilla": "formatos/nda_v3.docx", "vigente": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(formato)
    assert formato.nombre == "NDA estandar v2"

    r = api.post(f"/panel/catalogos/formatos/{formato.id}/eliminar", follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(formato)
    assert formato.vigente is False


def test_editar_y_eliminar_usuario(api, session, usuarios):
    admin = _login(api, session, usuarios, rol=Rol.admin_sistema)
    objetivo = usuarios[Rol.legal]
    r = api.post(
        f"/panel/catalogos/usuarios/{objetivo.id}/editar",
        data={"nombre": "Legal Renombrado", "email": objetivo.email, "rol": "legal", "activo": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(objetivo)
    assert objetivo.nombre == "Legal Renombrado"

    r = api.post(f"/panel/catalogos/usuarios/{objetivo.id}/eliminar", follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(objetivo)
    assert objetivo.activo is False

    # No puede desactivarse a si mismo.
    r = api.post(f"/panel/catalogos/usuarios/{admin.id}/eliminar", follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]
    session.refresh(admin)
    assert admin.activo is True


def test_navegacion_unidad_solicitante_solo_solicitudes_y_licitaciones(api, session, usuarios):
    """Unidad Solicitante: acceso solo a Nueva solicitud y Nueva licitación."""
    _login(api, session, usuarios, rol=Rol.unidad_solicitante)

    r = api.get("/panel/contratos/nuevo")
    assert r.status_code == 200
    r = api.get("/panel/licitaciones/nuevo")
    assert r.status_code == 200

    for ruta in ("/panel", "/panel/contratos", "/panel/vigencias", "/panel/metricas", "/panel/alertas"):
        r = api.get(ruta, follow_redirects=False)
        assert r.status_code == 303 and "error=" in r.headers["location"], ruta

    # El login sin 'siguiente' aterriza en un módulo que sí puede ver, no en /panel.
    r = api.post("/login", data={"email": usuarios[Rol.unidad_solicitante].email, "password": "clave12345"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/panel/contratos/nuevo"


def test_navegacion_jefatura_incluye_vigencias(api, session, usuarios):
    """Jefatura: Nueva solicitud, Nueva licitación y Gestión de vigencias — nada más."""
    _login(api, session, usuarios, rol=Rol.jefatura)

    for ruta in ("/panel/contratos/nuevo", "/panel/licitaciones/nuevo", "/panel/vigencias"):
        r = api.get(ruta)
        assert r.status_code == 200, ruta

    for ruta in ("/panel", "/panel/contratos", "/panel/metricas", "/panel/alertas"):
        r = api.get(ruta, follow_redirects=False)
        assert r.status_code == 303 and "error=" in r.headers["location"], ruta


def test_navegacion_legal_todo_menos_administracion(api, session, usuarios):
    """Legal: acceso a todos los módulos salvo Administración."""
    _login(api, session, usuarios, rol=Rol.legal)

    for ruta in (
        "/panel", "/panel/contratos", "/panel/contratos/nuevo", "/panel/licitaciones/nuevo",
        "/panel/vigencias", "/panel/metricas", "/panel/alertas",
    ):
        r = api.get(ruta)
        assert r.status_code == 200, ruta

    r = api.get("/panel/catalogos", follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"]


def test_administracion_solo_para_admin_sistema(api, session, usuarios):
    """El modulo Administracion completo (catalogos y parametros del sistema) es
    exclusivo de admin_sistema — cualquier otro rol, aunque este autenticado, no
    puede ni ver la pagina ni ejecutar sus acciones."""
    _login(api, session, usuarios, rol=Rol.legal)
    r = api.get("/panel/catalogos", follow_redirects=False)
    assert r.status_code == 303 and "error=" in r.headers["location"] and r.headers["location"].startswith("/panel?")

    r = api.post(
        "/panel/catalogos/unidades", data={"nombre": "Compras", "tipo": "interna"}, follow_redirects=False,
    )
    assert r.status_code == 303 and "error=" in r.headers["location"]

    r = api.post(
        "/panel/catalogos/contrapartes",
        data={"razon_social": "Intrusa SpA", "tipo": "proveedor"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and "error=" in r.headers["location"]

    from sqlalchemy import select
    from app.models.core import Contraparte, Unidad
    assert session.scalars(select(Unidad).where(Unidad.nombre == "Compras")).first() is None
    assert session.scalars(select(Contraparte).where(Contraparte.razon_social == "Intrusa SpA")).first() is None


def test_licitacion_activa_aparece_en_tablero(api, session, usuarios, unidad):
    _login(api, session, usuarios, rol=Rol.admin_licitaciones)
    r = api.post(
        "/panel/licitaciones/nuevo",
        data={"objeto": "Servicio de vigilancia", "unidad_solicitante_id": str(unidad.id), "moneda": "CLP"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    r = api.get("/panel")
    assert r.status_code == 200
    assert "Licitaciones en curso" in r.text
    assert "Servicio de vigilancia" in r.text


def test_transicion_a_aclaraciones_desde_ingreso(api, session, usuarios, unidad, contraparte):
    """Regresión: elegir 'aclaraciones' como destino debe funcionar sin un checkbox
    aparte de 'completitud' (se deriva del estado elegido, ver routes.py)."""
    u = _login(api, session, usuarios, rol=Rol.legal)
    from app.enums import LineaContrato
    from app.services.contratos import crear_contrato

    c = crear_contrato(
        session, codigo="CT-WEB-3", linea=LineaContrato.A_regular, objeto="x",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.unidad_solicitante], contraparte=contraparte,
    )
    session.commit()

    r = api.post(f"/panel/contratos/{c.id}/transicion", data={"hacia": "aclaraciones"}, follow_redirects=False)
    assert r.status_code == 303 and "ok=" in r.headers["location"]
    session.refresh(c)
    assert c.estado.value == "aclaraciones"
    assert c.retorno_a == "ingreso"
