# ROADMAP — Plan por etapas (propuesta, sin construir aún)

Contexto de negocio: ver [`CLAUDE.md`](CLAUDE.md).
Cada etapa termina con un **entregable verificable** para revisar una a una antes de avanzar.

---

## Objetivos a cubrir

1. **Sistema** que cumpla los objetivos del proceso: 3 líneas (A/B/C), estados
   transversales (Admisibilidad, Aclaraciones, Descartado), trazabilidad total y
   cierre por integración tipo WorkGes.
2. **Dashboard web local** para ver el estado de cada contrato **agrupado por mes**.
3. **Botón de descarga** del **reporte mensual**: estado de avance, vigencia y
   alertas de contratos vencidos / por vencer.

---

## Stack propuesto (a confirmar en Etapa 0)

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy.
- **Base de datos:** **PostgreSQL** (uso multiusuario en red). SQLite queda solo para
  desarrollo/pruebas locales. Respaldo con `pg_dump` programado.
- **Frontend:** server-rendered con Jinja2 + HTMX + un poco de JS (simple, sin build).
  Alternativa: React si se quiere más interacción.
- **Reportes:** **XLSX y PDF** — XLSX con `openpyxl` (varias hojas), PDF con WeasyPrint.
- **Despliegue:** la app corre en **un equipo servidor** de la red (servicio de Windows
  o contenedor); el resto accede por navegador vía `http://<servidor>:PORT`.
- **Autenticación:** login por usuario + control de acceso por rol (ver Etapa 7 / adelantable).

Motivo: mínimo de dependencias, buena generación de reportes, y Postgres soporta la
concurrencia de varios usuarios sin los bloqueos de SQLite. Todo reemplazable si se
prefiere Node/otro.

---

## Etapa 0 — Definiciones y diseño (sin código)

**Trabajo**
- Confirmar stack, si es monousuario local o compartido en red, y volumen estimado de contratos.
- Diccionario de datos definitivo (entidades y campos).
- Catálogo de estados por línea + tabla de transiciones permitidas (máquina de estados).
- Reglas de vigencia y alertas: días de "aviso previo" para renovación, umbral de
  "por vencer", definición de "vencido", "garantía por vencer", "solicitud estancada".
- Criterio de agrupación por mes del dashboard: ¿mes de ingreso, de firma o de
  vencimiento? (se puede ofrecer selector).
- Bosquejo (mockup) del dashboard y estructura del reporte mensual.
- Definir si habrá importación inicial desde planillas Excel existentes.

**Entregable verificable**
- Documento de diseño aprobado + diagrama del modelo de datos + tabla de estados/transiciones.

**Decisiones tomadas (2026-09-09)**
- [x] **Varios usuarios en red** → Postgres + despliegue en equipo servidor + login por rol.
- [x] **WorkGes se modela como módulo propio del sistema** (no hay integración externa; el
  "repositorio central" es una sección del propio sistema: vigencias, garantías, multas,
  renovaciones, hitos, administrador).
- [x] **Reporte en XLSX y PDF** (ambos).

**Decisiones tomadas (2026-09-09) — cont.**
- [x] **Alertas escalonadas de vencimiento/renovación: 90 / 60 / 30 días**
  (90 = informativa, 60 = atención, 30 = urgente).
- [x] **Carga de contratos** vía carpeta [`Contratos/`](Contratos/) del proyecto:
  `Planillas/` (Excel/CSV con datos para importar) y `Documentos/` (PDF/Word de los
  contratos). Sirve para la carga inicial y para incorporaciones futuras.
- [x] **Dashboard agrupa por mes con selector**: mes de ingreso / firma / vencimiento.

**Etapa 0: cerrada.** Entregables de diseño listos:
- [`docs/01-diccionario-de-datos.md`](docs/01-diccionario-de-datos.md) — modelo lógico completo.
- [`docs/02-maquina-de-estados.md`](docs/02-maquina-de-estados.md) — estados y transiciones A/B/C + invariantes.
- [`docs/03-plantilla-carga-contratos.md`](docs/03-plantilla-carga-contratos.md) — spec de la planilla de carga.
- [`Contratos/Planillas/_plantilla.xlsx`](Contratos/Planillas/_plantilla.xlsx) (+ `_plantilla.csv`) — plantilla real.

Decisión abierta menor (no bloquea Etapa 1): en Línea C Fase II, ¿estados propios
(`formalizacion_ajuste`, `constitucion_garantias`) o reutilizar el enum de contrato?
Ver nota en `docs/02-maquina-de-estados.md` §4.

---

## Etapa 1 — Núcleo de datos y motor de estados  ✅ completada y verificada (23/23 pruebas pasan)

**Trabajo** — hecho
- Proyecto base (FastAPI stub `/health`, SQLAlchemy 2.0, SQLite dev / PostgreSQL prod).
  Esquema por `Base.metadata.create_all` (`scripts/init_db.py`); Alembic se pospone a Etapa 2.
- Modelos en `app/models/`: `Usuario`, `Unidad`, `Contraparte`, `Parametro`,
  `FormatoEstandar`, `Contrato`, `Multa`, `Hito`, `Garantia`, `Documento`, `Licitacion`,
  `EventoEstado`.
- Motor de estados en `app/state_machine/`: transiciones declarativas por línea (A/B/C) +
  licitación, guards/efectos, y registro automático de `EventoEstado` (quién, cuándo,
  de/a, comentario, `retorno_a`).
- Servicios en `app/services/`: `crear_contrato`, `crear_licitacion`, `adjudicar_licitacion`,
  parámetros.
- Reglas implementadas: Línea C no firma sin garantía de cumplimiento vigente (Gate 2);
  Línea B no tiene `elaboracion` y se bloquea si el formato fue modificado (checksum);
  `elaboracion` exige abogado; `vigente` exige administrador + vigencia; aprobación de
  Gerencia por monto; `aclaraciones` con `retorno_a`; `descartado` transversal y terminal.
- Decisión resuelta: Fase II de Línea C usa estados propios `formalizacion_ajuste` y
  `constitucion_garantias` (ver `docs/02` §4.2).

**Entregable verificable** — ✅ suite `pytest` **ejecutada: 23/23 pruebas pasan** (con `uv`,
Python 3.12). Cubre: recorrido completo A / B / C, Aclaraciones ida y vuelta, Descartado,
invariantes y trazabilidad. `python -m scripts.demo_flujos` recorre los 3 flujos e imprime
la trazabilidad. Cómo correrlo: [`README_DEV.md`](README_DEV.md).

---

## Etapa 2 — API y carga de datos  ✅ completada y verificada (38/38 pruebas pasan)

**Trabajo** — hecho (código en `app/api/`)
- API FastAPI (`app.main:app`, `create_app()` en `app/api/app.py`):
  - Catálogos: `unidades`, `usuarios`, `contrapartes`, `formatos`, `parametros`.
  - Contratos: crear, listar (con filtros línea/estado/unidad/contraparte/administrador/abogado),
    **ficha completa** (`GET /contratos/{id}` → contrato + garantías + hitos + multas +
    documentos + **historial/línea de tiempo**), `PATCH`, sub-recursos
    (`/garantias`, `/hitos`, `/multas`, `/documentos`) y `POST /contratos/{id}/transiciones`.
  - Licitaciones: crear, listar, ficha, `PATCH`, `/transiciones`, `/adjudicar`
    (crea el contrato de Línea C), `/garantias`.
  - Importación: `POST /importaciones/contratos` (lee de `Contratos/Planillas/`).
- Errores del dominio traducidos a HTTP: `RolNoAutorizado`→403, `TransicionNoPermitida`→409,
  `PrecondicionNoCumplida`→422, `ValueError` de servicios→400.
- Importador Excel/CSV (`app/services/importador.py`): hojas Contratos + Garantías + Hitos,
  validación por fila (encabezados, enums, fechas coherentes, formato para Línea B),
  reporte `{creados, actualizados, errores[fila+motivo], advertencias}`, re-importación
  por `codigo_externo` (actualiza, no duplica el contrato), auto-alta de unidades /
  contrapartes / usuarios faltantes (con advertencia).
- Scripts: `scripts/importar.py`, `scripts/crear_planilla_ejemplo.py`
  (genera `Contratos/Planillas/ejemplo.xlsx`).

**Entregable verificable** — ✅ **38/38 pruebas pasan** (`uv` + Python 3.12). Nuevas:
`tests/test_api_contratos.py`, `tests/test_api_licitaciones.py`, `tests/test_api_importacion.py`.
`python -m scripts.crear_planilla_ejemplo && python -m scripts.importar ejemplo.xlsx`
importa 3 contratos de ejemplo sin errores. Servir la API: `uvicorn app.main:app --reload`
(docs en `/docs`).

---

## Etapa 3 — Dashboard web local  ✅ completada y verificada (47/47 pruebas pasan)

**Trabajo** — hecho (`app/web/`, server-rendered Jinja2, sin build ni JS externo)
- `GET /panel`: contratos **agrupados por mes** con **selector ingreso / firma /
  vencimiento**, y su equivalente JSON `GET /panel.json` (consumido por las pruebas).
- Filtros (form GET): línea, estado, unidad, administrador, contraparte, rango `desde`/`hasta`
  sobre la fecha de agrupación.
- Tabla por grupo: código (enlace a la ficha), contraparte, objeto, línea, estado, monto,
  fin de vigencia, días para vencer y **semáforo**
  (`vigente` / `por_vencer` / `en_renovacion` / `vencido` / `en_tramite` / `sin_vigencia` /
  `cerrado`, con nivel 90/60/30).
- KPIs: total, por línea A/B/C, vigentes, por vencer, vencidos, en renovación, monto por moneda.
- `GET /panel/contratos/{id}`: ficha con **línea de tiempo** (trazabilidad), garantías,
  hitos, multas y documentos.
- Servicio `app/services/dashboard.py` (`construir_dashboard`, `semaforo_de`,
  `opciones_filtros`); lectura común factorizada en `app/services/consultas.py`.

**Entregable verificable** — ✅ **47/47 pruebas** (`tests/test_web_dashboard.py` cubre
indicadores, semáforo, agrupación por vencimiento/ingreso, filtros y rango de fechas,
HTML del panel y de la ficha, redirección `/`→`/panel`). Verificado además en navegador
con la planilla de ejemplo (agrupación por mes, semáforos y ficha de detalle).
Levantar: `uvicorn app.main:app --reload` → `http://127.0.0.1:8000/panel`
(o `.claude/launch.json` → `preview panel`).

---

## Etapa 4 — Motor de alertas  ✅ completada y verificada

**Trabajo** — hecho (`app/services/alertas.py`)
- `calcular_alertas` (al vuelo, no se almacenan): `contrato_vencido`, `contrato_por_vencer`
  (90/60/30), `renovacion_proxima`, `garantia_vencida`, `garantia_por_vencer`,
  `hito_atrasado`, `solicitud_estancada` (aclaraciones > `aclaraciones_dias_alerta`).
  Cada alerta trae nivel, contrato, título, detalle, fecha de referencia y días; se ordenan
  por severidad.
- API: `GET /alertas` (filtros `tipo`/`nivel`), `GET /alertas/resumen`.
- Web: `GET /panel/alertas` (tabla con enlace al contrato) + **píldora con el conteo en `/panel`**.

**Entregable verificable** — ✅ `tests/test_alertas.py`: cartera con fechas conocidas cae en
la categoría correcta; solicitud estancada; API y web.

---

## Etapa 5 — Reporte mensual descargable  ✅ completada y verificada

**Trabajo** — hecho (`app/services/reportes.py`)
- **Botón "Descargar reporte del mes"** en `/panel` (selector de mes + formato XLSX/PDF)
  → `GET /panel/reporte?periodo=AAAA-MM&formato=xlsx|pdf` (respuesta `attachment`).
- Contenido: **Resumen ejecutivo** (conteos por estado/línea, montos, alertas), **Detalle**
  de cada contrato (avance, vigencia, días restantes, semáforo), **Vencen en el mes**,
  **Alertas** (vencidos / por vencer / atrasos), **Garantías** (vigente / por vencer / vencida).
- **XLSX** (openpyxl, hojas Resumen/Detalle/Vencen/Alertas/Garantias) y **PDF** (fpdf2,
  sin dependencias de sistema). Archivo `reporte_contratos_AAAA-MM.<fmt>`.
- CLI: `python -m scripts.reporte 2026-03 xlsx|pdf` (guarda en `reportes/`).

**Entregable verificable** — ✅ `tests/test_reportes.py`: estructura de datos, XLSX con sus
hojas, PDF válido (`%PDF`), endpoint con `Content-Disposition: attachment`.

---

## Etapa 6 — Empaquetado y operación local  ✅ completada y verificada

**Trabajo** — hecho
- **`run.bat`**: usa `uv` si está disponible, si no crea un venv; prepara la base, abre el
  navegador y levanta `uvicorn`.
- Respaldo/restauración SQLite: `python -m scripts.respaldo` /
  `python -m scripts.respaldo restaurar <archivo>` (respaldos en `respaldos/`; guarda copia
  de la base actual antes de restaurar). En PostgreSQL: `pg_dump`.
- **Manual de uso**: [`docs/04-manual-de-uso.md`](docs/04-manual-de-uso.md).

**Entregable verificable** — ✅ `tests/test_operacion.py` (respaldo → modificar → restaurar).
Ciclo end-to-end probado con `scripts.init_db` + `scripts.importar` + `scripts.reporte` y
el panel en el navegador.

---

## Etapa 7 — Extensiones  ✅ parcialmente entregada

Hecho y verificado:
- **Métricas de proceso** (`app/services/metricas.py`): permanencia media/mediana/máx por
  estado desde la trazabilidad, cuello de botella, throughput a "vigente" por mes, tasa de
  descarte. API `GET /metricas`, web `GET /panel/metricas`. (`tests/test_metricas.py`)
- **Verificación de formato Línea B** (`app/services/formatos.py`):
  `POST /formatos/{id}/verificar` sube un archivo y compara su SHA-256 con el clausulado
  estándar.
- **Autenticación mínima** (`app/services/auth.py`): hash PBKDF2, tokens HMAC, `POST /auth/login`,
  `/login` web con cookie. Desactivada por defecto (`AUTH_REQUIRED`); con ella activa,
  `/panel` pide ingreso y los endpoints de escritura exigen token. (`tests/test_auth.py`)

Pendiente (requiere decisiones o sistemas externos):
- Integración real con **WorkGes** (necesita su API/exportación).
- **Notificaciones por correo** (necesita credenciales SMTP y política de envío).
- Control de acceso por rol *fino* por endpoint (hoy la protección es "autenticado sí/no").

---

## Estado global

Etapas 0–6 completas y verificadas; Etapa 7 parcial. **63/63 pruebas pasan**
(`uv` + Python 3.12). Pedidos del usuario cubiertos: (1) sistema con las 3 líneas y
trazabilidad total, (2) dashboard por mes con selector, (3) botón de reporte mensual
XLSX/PDF con avance, vigencia y alertas de vencidos.
