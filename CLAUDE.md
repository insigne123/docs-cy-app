# CLAUDE.md — Proyecto: Sistema de Contratos y Licitaciones

> Contexto del proceso de negocio, extraído de `Documentación del proceso/`
> (PDF "Mapa del Proceso", `índice ... .docx` y 7 imágenes de mapa mental).
> Este archivo evita tener que volver a explicar el proceso. Actualizar cuando cambien las reglas.

---

## 1. Idea central

Manual de procedimiento (y sistema a construir) para gestionar **contratos y licitaciones**
mediante **tres rutas diferenciadas por riesgo y complejidad** que comparten estados
transversales y un cierre común: la **integración en WorkGes** (repositorio central de
vigencias, garantías, multas, renovaciones e hitos).

**Objetivos del sistema:**
- Vías predecibles y eficientes para contratos y licitaciones.
- Trazabilidad total de la información (incluidos los procesos descartados).
- Blindaje frente a riesgos legales y cumplimiento normativo.
- No sacrificar agilidad operativa.

**Alcance:** Unidades Solicitantes y áreas internas.

---

## 2. Roles

| Rol | Responsabilidad |
|---|---|
| **Unidad Solicitante** | Ingresa solicitudes, resuelve aclaraciones, valida contenido con la contraparte externa, coordina firmas. |
| **Jefatura de la Unidad** | Aprobación inicial (coherencia y necesidad) antes de derivar a Legal. |
| **Área Legal** | Admisibilidad jurídica, redacción/adecuación de contratos, visación, integración al sistema, mantención de formatos estándar (autogestionados). |
| **Área Administrativa de Licitaciones** | Control administrativo de licitaciones: bases, registro de antecedentes, envío formal de ofertas. |
| **Área Financiera** | Evaluación económica. **Facultad exclusiva** de emitir/gestionar garantías (boletas, pólizas, fiel cumplimiento, seriedad). |
| **Área Técnica / Operativa** | Propuesta técnica en licitaciones, examen de admisibilidad, revisión de bases. Designa al **administrador de contrato**. |
| **Gerencia** | Aprobaciones estratégicas según monto; factibilidad preliminar en licitaciones. |

---

## 3. Estados transversales (aplican en cualquier etapa)

- **Admisibilidad** — filtro de calidad jurídica inicial antes de invertir en redacción.
  - *Admisibilidad I*: revisión de antecedentes mínimos / completitud.
  - *Admisibilidad II*: asignación formal del abogado responsable.
- **Aclaraciones** — la solicitud se detiene y vuelve a la Unidad Solicitante para
  corregir/complementar; luego retorna al punto donde estaba.
- **Descartado** — cierre definitivo y archivo del proceso en cualquier fase, por
  inviabilidad técnica o legal, decidido por el área responsable.

---

## 4. Línea A — Flujo Regular / Abastecimiento

Ruta estándar con redacción legal a medida.

1. **Ingreso de Solicitud** — Unidad Solicitante. Formulario + antecedentes; validación automática de completitud.
2. **Aprobación** — Jefatura. Coherencia y necesidad.
3. **Admisibilidad** — Área Legal (I: antecedentes; II: asignación de abogado). Si falta info → **Aclaraciones**.
4. **Elaboración del Documento** — Abogado. Redacción, revisión o adecuación del contrato.
5. **Visación** — Legal / Solicitante. Validación final cruzada del contenido.
   Con tercero externo: la Unidad Solicitante lidera la *Visación con Contraparte*.
6. **Firma** — Legal. Suscripción electrónica o física en plataforma.
7. **Integración** — Admin de Contratos. Archivo en WorkGes con vigencia, renovaciones,
   causales de término, multas, garantías, hitos y administrador asignado.

---

## 5. Línea B — Flujo Express / Autogestionado (servicios "Expro")

Sub-flujo de vía rápida. **Bypass de la redacción del abogado.**

Pasos: **Ingreso → Admisibilidad I → Visación → Firma → Integración**
(se omiten Aprobación de Jefatura y Elaboración).

**Condiciones de uso (estrictas):**
- Solicitudes repetitivas, comunes y de **bajo riesgo legal**.
- **Formato estándar pre-aprobado** por Área Legal / Fiscalía (matriz aprobada).
- Prohibido modificar el clausulado o agregar cláusulas especiales.
- En Admisibilidad I se verifica que el formato **no** fue alterado.

**Matriz de decisión Regular vs Autogestionado:**

| Criterio | Flujo Regular | Autogestionado |
|---|---|---|
| Riesgo legal | Alto / variable | Bajo |
| Personalización de cláusulas | Permitida | Prohibida |
| Intervención de Legal | Redacción a medida | Solo control de estándar y admisibilidad |
| Tiempo de tramitación | Extendido según complejidad | Optimizado / reducido |
| Requisito previo | Antecedentes completos | Matriz previamente aprobada por Fiscalía |

**Beneficios:** más autonomía, menor carga legal, reducción drástica de tiempos.

---

## 6. Línea C — Flujo Complejo / Licitaciones Externas

### Fase I — Pre-Adjudicación
1. **Ingreso de antecedentes** — Área Admin. Registro/descarga de bases.
2. **Examen de admisibilidad** — filtro multidisciplinario (Técnica, Financiera, Legal, Gerencia): inhabilidades, factibilidad, plazos, garantías.
3. **Revisión de bases** — Legal + Técnica. Multas, causales de término → **Informe de Riesgos y Validación Final**.
4. **Preparación y presentación de oferta**:
   - Área Técnica → propuesta técnica.
   - Área Financiera → propuesta económica + **garantía de seriedad**.
   - Área Legal/Admin → revisión documental y carga formal en plataforma.
5. **Resultado**:
   - *Adjudicado* → pasa a Fase II.
   - *No adjudicado* → archivo + análisis interno para mejora continua.

### Fase II — Formalización (solo si adjudicado; 4 "gates" secuenciales)
- **Gate 1 — Revisión y ajuste del contrato** — Legal. Coherencia con la oferta: multas, plazos, reajustes.
- **Gate 2 — Constitución de garantías** — Financiera. Boletas, pólizas, fiel cumplimiento. **Requisito estricto previo a la firma.**
- **Gate 3 — Firma** — Rep. Legal / Área Legal. Electrónica o presencial + verificación de anexos.
- **Gate 4 — Integración** — Admin de Contratos. Hitos, vencimiento de garantías, designación del administrador.
- **Inicio de ejecución contractual** — Área Técnica. Activa el control de cumplimiento.

---

## 7. Convergencia: WorkGes

Las 3 líneas terminan integrándose en **WorkGes**, repositorio centralizado. Variables
críticas obligatorias al integrar: **vigencia, renovaciones, causales de término, multas,
garantías, hitos, administrador asignado**.

De WorkGes se obtiene:
- **Trazabilidad total** (incluye descartes).
- **Reportabilidad legal** — métricas de tiempos, cuellos de botella, mapeo de riesgos recurrentes.
- **Evolución anual** — auditoría y actualización del propio procedimiento.

---

## 8. Glosario de estados del ciclo de vida contractual

| Estado | Descripción corta |
|---|---|
| Ingreso de Solicitud | Carga de formulario + documentos obligatorios; validación automática de completitud. |
| Admisibilidad I | Análisis de antecedentes mínimos obligatorios. |
| Admisibilidad II | Asignación formal de la solicitud a un abogado. |
| Aclaraciones | Estado transversal: devuelve a la Unidad Solicitante para corregir/complementar. |
| Elaboración del Documento | Redacción / revisión / adecuación del borrador. |
| Visación | Validación y control definitivo del texto antes de firmar (incl. Visación con Contraparte). |
| Firma | Suscripción física o electrónica en plataforma. |
| Integración / Registro | Post-firma: archivo en WorkGes + inscripción de variables críticas. |
| Descartado | Estado transversal: término definitivo y archivo en cualquier fase. |

---

## 9. Archivos fuente

Carpeta `Documentación del proceso/`:
- `Mapa del Proceso (Contratos y Licitaciones).pdf` — 11 láminas; fuente más completa.
- `índice  Proceso de Contratos y Licitaciones.docx` — texto normativo (roles, etapas, definiciones).
- `Proceso General.png` — índice raíz (6 ramas).
- `Objetivos y Alcances.png` — objetivos y alcance.
- `Roles Principales.png` / `Roles Principales (1).png` — idénticos; roles resumidos.
- `Flujo Abastecimiento (2).png` — hitos de Línea A.
- `Flujo Autogestionado.png` — Línea B.
- `Flujo Proceso Licitaciones.png` — Línea C.
- `Estados Transversales.png` — Aclaraciones y Descartado.

---

## 10. Estado del proyecto

- **2026-09-09**: Analizada la documentación del proceso. Redactado este CLAUDE.md y
  `ROADMAP.md` con el plan por etapas. **Aún no se ha construido código.**
- **Decisiones tomadas (Etapa 0 cerrada)**:
  - Multiusuario en red → PostgreSQL + app en equipo servidor + login por rol.
  - WorkGes se modela como módulo propio del sistema.
  - Reportes en XLSX y PDF.
  - Alertas de vencimiento/renovación escalonadas: 90 / 60 / 30 días.
  - Carga de contratos por la carpeta `Contratos/` (`Planillas/` + `Documentos/`),
    para carga inicial y futura.
  - Dashboard agrupa por mes con selector: ingreso / firma / vencimiento.
- **Etapa 0 completada** — entregables de diseño en `docs/`:
  `01-diccionario-de-datos.md`, `02-maquina-de-estados.md`,
  `03-plantilla-carga-contratos.md`, y `Contratos/Planillas/_plantilla.xlsx` (+ `.csv`).
- **Etapa 1 completada y verificada** — `app/` (modelos SQLAlchemy 2.0, motor de estados,
  servicios). Decisión resuelta: Línea C Fase II usa estados propios `formalizacion_ajuste`
  y `constitucion_garantias`.
- **Etapa 2 completada y verificada** — `app/api/` (FastAPI): catálogos, contratos
  (CRUD + ficha con línea de tiempo + transiciones + sub-recursos), licitaciones
  (+ adjudicar), importador Excel/CSV desde `Contratos/Planillas/`. Errores del dominio
  → HTTP 403/409/422/400.
- **Etapa 3 completada y verificada** — `app/web/` (panel Jinja2, sin build): `GET /panel`
  con contratos **agrupados por mes** (selector ingreso/firma/vencimiento), filtros,
  **semáforo de vigencia** (90/60/30), KPIs, y `GET /panel/contratos/{id}` con línea de
  tiempo. `GET /panel.json` = mismos datos en JSON.
- **Etapa 4 completada** — `app/services/alertas.py`: alertas al vuelo (vencidos, por vencer,
  garantías, hitos atrasados, solicitudes estancadas). `GET /alertas`, `GET /panel/alertas`,
  píldora de conteo en `/panel`.
- **Etapa 5 completada** — `app/services/reportes.py`: **botón "Descargar reporte del mes"**
  en `/panel` → `GET /panel/reporte?periodo=AAAA-MM&formato=xlsx|pdf`. XLSX (openpyxl) y
  PDF (fpdf2). `scripts/reporte.py` guarda en `reportes/`.
- **Etapa 6 completada** — `run.bat` (uv o venv), `scripts/respaldo.py`,
  `docs/04-manual-de-uso.md`.
- **Etapa 7 parcial** — métricas de proceso (`GET /metricas`, `/panel/metricas`),
  verificación de formato Línea B (`POST /formatos/{id}/verificar`), auth mínima
  (`app/services/auth.py`, `POST /auth/login`, `/login`; `AUTH_REQUIRED` off por defecto).
  Pendiente: WorkGes real, correo, roles finos por endpoint.
- **63/63 pruebas pasan** (con `uv` + Python 3.12; el equipo no tiene Python nativo:
  `uv run --no-project --python 3.12 --with-requirements requirements-dev.txt pytest`).
  Stack: FastAPI + SQLAlchemy, SQLite en desarrollo / PostgreSQL en producción.
  Servir todo: `uvicorn app.main:app --reload` (panel en `/panel`, API docs en `/docs`).
  Instrucciones en `README_DEV.md` y `docs/04-manual-de-uso.md`.
