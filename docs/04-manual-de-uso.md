# 04 — Manual de uso

Operación local del Sistema de Contratos y Licitaciones. Para el detalle técnico ver
[`../README_DEV.md`](../README_DEV.md).

## Arranque

- **Doble clic en `run.bat`** (en la raíz del proyecto). Crea la base si no existe, levanta
  el servidor y abre el panel en el navegador.
- Manual: `uvicorn app.main:app --host 127.0.0.1 --port 8000` y abrir
  `http://127.0.0.1:8000/panel`.
- Detener: `Ctrl+C` en la ventana del servidor.

## Panel (`/panel`)

- **Agrupar por**: ingreso / firma / vencimiento (cambia el mes con que se agrupan los contratos).
- **Filtros**: línea, estado, unidad, administrador, contraparte, rango de fechas. "Limpiar" quita todo.
- **Semáforo**: `vigente`, `por_vencer` (90/60/30 días), `en_renovacion`, `vencido`,
  `en_tramite` (aún no vigente), `sin_vigencia` (vigente sin fecha fin), `cerrado`.
- Clic en un **código** abre la ficha: datos, línea de tiempo (trazabilidad), garantías,
  hitos, multas y documentos.
- **Alertas**: la píldora superior lleva a `/panel/alertas` (vencidos, por vencer,
  garantías, hitos atrasados, solicitudes estancadas).
- **Métricas de proceso**: `/panel/metricas` (permanencia por estado, cuello de botella,
  contratos que llegan a "vigente" por mes, tasa de descarte).

## Reporte mensual

En el panel: elegir el mes, formato **XLSX** o **PDF**, y **"Descargar reporte del mes"**.
El reporte incluye resumen ejecutivo, detalle de cada contrato con estado de avance y
vigencia, alertas de vencidos / por vencer, y garantías.

Por línea de comandos (queda en `reportes/`):

```
python -m scripts.reporte 2026-03 xlsx
python -m scripts.reporte 2026-03 pdf
```

## Carga de contratos

1. Colocar la planilla en `Contratos/Planillas/` (formato:
   [`03-plantilla-carga-contratos.md`](03-plantilla-carga-contratos.md);
   `_plantilla.xlsx` es la referencia).
2. `python -m scripts.importar mi_planilla.xlsx`, o `POST /importaciones/contratos`.
3. Revisar las **advertencias** (unidades / contrapartes / usuarios creados
   automáticamente y roles tentativos).

## Ciclo de un contrato (por la API)

1. `POST /contratos` (Línea A o B) — devuelve el `id`.
2. `POST /contratos/{id}/transiciones` con `{ "hacia": "<estado>", "usuario_id": N, "comentario": "..." }`
   para avanzar. Los datos que exige cada paso (abogado, garantía, administrador,
   fin de vigencia) se cargan con `PATCH /contratos/{id}` o los sub-recursos
   (`/garantias`, `/hitos`, ...).
3. Licitaciones: `POST /licitaciones` → `/transiciones` (Fase I) → `POST /licitaciones/{id}/adjudicar`
   (crea el contrato Línea C) → `/transiciones` del contrato (Fase II).

La documentación interactiva de la API está en `/docs`.

## Respaldo

```
python -m scripts.respaldo                       # crea respaldos/backup_AAAAMMDD_HHMMSS.db
python -m scripts.respaldo restaurar <archivo>   # restaura (SQLite)
```

En PostgreSQL usar `pg_dump` / `pg_restore`.

## Autenticación (opcional)

Desactivada por defecto (uso local). Para activarla en el servidor de red, en `.env`:

```
AUTH_REQUIRED=true
SECRET_KEY=<una-cadena-larga-y-secreta>
```

Con ella activa, `/panel` pide ingreso en `/login` y los endpoints de escritura exigen
token (`POST /auth/login` → `Authorization: Bearer <token>`). Crear usuarios con
contraseña: `POST /usuarios` con el campo `password`.
