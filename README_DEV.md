# Guía de desarrollo

Núcleo de datos + motor de estados + API REST + importador + panel web + alertas +
reportes + métricas. Contexto: [`CLAUDE.md`](CLAUDE.md) · Plan: [`ROADMAP.md`](ROADMAP.md) ·
Diseño: [`docs/`](docs/) · Uso: [`docs/04-manual-de-uso.md`](docs/04-manual-de-uso.md) ·
**Desplegar en producción (online + Postgres en la nube): [`docs/05-despliegue-produccion.md`](docs/05-despliegue-produccion.md).**

> **Estado:** Etapas 0–6 completas + Etapa 7 parcial. La suite pasa **63/63**
> (ejecutada con `uv` + Python 3.12).

## Requisitos

- Python 3.10 o superior, **o** [`uv`](https://docs.astral.sh/uv/) (que baja Python solo).

## Opción 1 — con `uv` (recomendada, no requiere instalar Python)

```bat
winget install --id=astral-sh.uv -e
uv run --no-project --python 3.12 --with-requirements requirements-dev.txt pytest
```

## Opción 2 — con Python instalado

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```

Cobertura opcional: `pytest --cov`

### Qué cubren las pruebas

| Archivo | Verifica |
|---|---|
| `tests/test_linea_a.py` | Flujo Regular completo (ingreso → vigente), ramo de aprobación de Gerencia por monto, rechazo por rol. |
| `tests/test_linea_b.py` | Flujo Autogestionado completo, ausencia del estado `elaboracion`, rechazo si el formato fue modificado, desvío por Gerencia. |
| `tests/test_linea_c.py` | Licitación Fase I → adjudicación → Fase II (4 gates) → vigente; bloqueo de firma sin garantía; “no adjudicada” exige análisis interno. |
| `tests/test_aclaraciones.py` | Ida y vuelta a `aclaraciones`; sólo se puede volver al estado guardado en `retorno_a`. |
| `tests/test_descartado.py` | Descarte desde cualquier estado; es terminal; exige motivo; aplica también a licitaciones. |
| `tests/test_invariantes.py` | Abogado obligatorio para `elaboracion`; administrador + vigencia para `vigente`; garantía para `firma` cuando el contrato la exige. |
| `tests/test_trazabilidad.py` | El historial queda ordenado, encadenado y con autor/rol/comentario; expedientes distintos no se mezclan. |
| `tests/test_api_contratos.py` | Crear + ficha, flujo A completo por HTTP, rechazos 403/409/422, garantía previa a firma, filtros de listado. |
| `tests/test_api_licitaciones.py` | Fase I por HTTP, `/adjudicar` (201 → contrato Línea C), Fase II hasta `vigente`, "no adjudicada" exige análisis. |
| `tests/test_api_importacion.py` | Importar XLSX/CSV: crea, re-importa (actualiza), reporta errores por fila; endpoint `/importaciones/contratos`. |
| `tests/test_web_dashboard.py` | Panel: KPIs, semáforo (vigente/por vencer/en renovación/vencido/en trámite), agrupación por vencimiento e ingreso, filtros y rango de fechas, HTML de panel y ficha, redirección `/`→`/panel`. |
| `tests/test_alertas.py` | Alertas por tipo/nivel (vencido, por vencer, renovación, garantía, hito, estancada); resumen; API y web. |
| `tests/test_reportes.py` | Datos del reporte, XLSX (hojas), PDF (`%PDF`), endpoint `/panel/reporte` con `attachment`. |
| `tests/test_metricas.py` | Permanencia por estado, throughput, tasa de descarte; API `/metricas` y web. |
| `tests/test_auth.py` | Hash PBKDF2 y tokens; con `AUTH_REQUIRED` los endpoints de escritura exigen token; login web/JSON. |
| `tests/test_operacion.py` | Respaldo y restauración de la base SQLite. |

## Demo manual (sin base real)

```bat
uv run --no-project --python 3.12 --with-requirements requirements.txt python -m scripts.demo_flujos
```

(o `python -m scripts.demo_flujos` si tienes el entorno activado). Crea todo en una base
SQLite en memoria, recorre los tres flujos e imprime la trazabilidad.

## Crear el esquema en una base real

**Desarrollo (SQLite):**
```bat
python -m scripts.init_db
```

**Producción (PostgreSQL) — con Alembic:**
```bat
alembic upgrade head
```

`DATABASE_URL` (ver `.env.example`) controla el destino; acepta también el formato
`postgres://` que entregan Railway/Render. Ver [`docs/05-despliegue-produccion.md`](docs/05-despliegue-produccion.md)
para el despliegue completo (app online + base en la nube).

## Levantar la aplicación

**Doble clic en `run.bat`** (prepara la base, abre el navegador y levanta el servidor), o:

```bat
uvicorn app.main:app --reload
```

- **Panel web:** `http://127.0.0.1:8000/panel` — contratos por mes (selector
  ingreso/firma/vencimiento), filtros, semáforo, KPIs, píldora de alertas, botón de
  reporte. Sub-páginas: `/panel/contratos/{id}` (ficha + línea de tiempo),
  `/panel/alertas`, `/panel/metricas`. `/panel.json` = datos del panel en JSON.
- **Reporte:** `GET /panel/reporte?periodo=AAAA-MM&formato=xlsx|pdf` (descarga).
- **API + docs:** `http://127.0.0.1:8000/docs`. Endpoints: `/auth/login`,
  `/unidades` `/usuarios` `/contrapartes` `/formatos` (`/formatos/{id}/verificar`)
  `/parametros`, `/contratos` (CRUD + ficha + `/transiciones` + sub-recursos),
  `/licitaciones` (+ `/adjudicar`), `/importaciones/contratos`, `/alertas`
  (`/alertas/resumen`), `/metricas`.

Con Claude Code / el navegador integrado también sirve `preview panel` (usa
`.claude/launch.json`).

## Autenticación (opcional, para el servidor de red)

En `.env`: `AUTH_REQUIRED=true` y `SECRET_KEY=<cadena-larga>`. Entonces `/panel` exige
ingreso (`/login`) y los endpoints de escritura piden `Authorization: Bearer <token>`
(`POST /auth/login`). Crear usuarios con clave: `POST /usuarios` con `password`.

## Importar una planilla

```bat
python -m scripts.crear_planilla_ejemplo
python -m scripts.importar ejemplo.xlsx
```

El importador lee la hoja `Contratos` (y opcionales `Garantias`, `Hitos`) de
`Contratos/Planillas/`. Formato de columnas: [`docs/03-plantilla-carga-contratos.md`](docs/03-plantilla-carga-contratos.md).
Re-importar un `codigo_externo` existente **actualiza** el contrato (no lo duplica).

## Estructura

```
app/
  config.py            configuración (env / .env): DATABASE_URL, AUTH_REQUIRED, SECRET_KEY
  database.py          engine + sesión + crear_todo()
  enums.py             enumeraciones del dominio
  main.py              app ASGI (create_app)
  models/              modelos SQLAlchemy (core, contrato, licitacion, evento)
  state_machine/       transitions / guards / engine (MotorEstados) / repositories
  services/            crear_contrato, crear_licitacion, adjudicar_licitacion, importador,
                       consultas, dashboard, alertas, reportes, metricas, formatos, auth,
                       parametros
  api/
    app.py deps.py errors.py schemas.py
    routers/           auth, catalogos, contratos, licitaciones, importacion, alertas, metricas
  web/
    routes.py          panel, alertas, métricas, ficha, reporte, login
    templates/         base, dashboard, detalle, alertas, metricas, login
scripts/               init_db, demo_flujos, importar, crear_planilla_ejemplo, reporte,
                       respaldo, crear_admin (bootstrap de usuario en producción)
alembic/               migraciones (alembic upgrade head)
run.bat                arranque local (uv o venv)
Procfile, render.yaml  despliegue en Railway / Render (ver docs/05)
tests/                 suite pytest (63)
```
