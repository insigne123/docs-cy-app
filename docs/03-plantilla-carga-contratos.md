# 03 — Plantilla de carga de contratos

Especificación de la planilla que se deposita en
[`../Contratos/Planillas/`](../Contratos/Planillas/) para la carga inicial y las
incorporaciones futuras. El importador (Etapa 2) la lee y crea/actualiza registros.

Archivo de referencia generado: `../Contratos/Planillas/_plantilla.xlsx`
(equivalente en `_plantilla.csv`, solo hoja **Contratos**).

Reglas:
- **Una fila = un contrato.**
- La primera fila es el encabezado; los nombres de columna deben respetarse tal cual.
- Fechas en formato **`AAAA-MM-DD`**.
- Campos de lista aceptan solo los valores indicados (ver hoja **Listas**).
- `codigo_externo` es la llave para relacionar las hojas **Garantías** y **Hitos** con
  cada contrato, y para re-importar sin duplicar (si ya existe, se actualiza).
- Números sin separador de miles; decimales con punto.

---

## Hoja `Contratos`

| Columna | Req | Tipo / valores | Ejemplo | Notas |
|---|---|---|---|---|
| `codigo_externo` | recomendado | texto | `SC-1042` | código propio previo. Si se deja vacío, el sistema asigna `CT-AAAA-####` y no se podrá enlazar Garantías/Hitos por planilla |
| `linea` | sí | `A` \| `B` \| `C` | `A` | A=Regular/Abastecimiento, B=Autogestionado, C=Licitación |
| `objeto` | sí | texto | `Servicio de aseo oficinas central` | |
| `categoria` | no | `servicio` \| `suministro` \| `arriendo` \| `obra` \| `licencia` \| `otro` | `servicio` | |
| `unidad_solicitante` | sí | texto (nombre de unidad) | `Operaciones` | debe existir o se crea en el catálogo |
| `solicitante_email` | sí | email | `jperez@empresa.cl` | usuario que ingresó / responsable |
| `contraparte_razon_social` | sí | texto | `Aseos del Sur SpA` | |
| `contraparte_rut` | no | texto | `76.123.456-7` | |
| `contraparte_contacto_email` | no | email | `contacto@aseosdelsur.cl` | |
| `abogado_email` | no | email | `mlopez@empresa.cl` | si ya está asignado |
| `administrador_email` | no | email | `rgomez@empresa.cl` | administrador del contrato |
| `formato_estandar` | solo B | texto (nombre del formato) | `NDA estándar v3` | obligatorio si `linea = B` |
| `licitacion_codigo` | solo C | texto | `LIC-2025-0031` | si el contrato proviene de una licitación |
| `estado_actual` | sí | ver hoja **Listas** → `estado_contrato` | `vigente` | estado en que se encuentra hoy |
| `monto` | no | número | `18500000` | |
| `moneda` | no | `CLP` \| `UF` \| `USD` \| `EUR` \| `otro` | `CLP` | requerido si hay `monto` |
| `requiere_garantia` | no | `si` \| `no` | `no` | default `no` |
| `fecha_ingreso` | sí | fecha | `2025-03-04` | |
| `fecha_aprobacion_jefatura` | no | fecha | `2025-03-06` | |
| `fecha_admisibilidad` | no | fecha | `2025-03-12` | cierre de Admisibilidad II |
| `fecha_visacion` | no | fecha | `2025-03-20` | |
| `fecha_firma` | no | fecha | `2025-03-25` | |
| `fecha_integracion` | no | fecha | `2025-03-28` | |
| `fecha_inicio_vigencia` | no | fecha | `2025-04-01` | |
| `fecha_fin_vigencia` | condic. | fecha | `2026-03-31` | obligatoria si `vigencia_indefinida = no` y `estado_actual` es `vigente`/`terminado` |
| `vigencia_indefinida` | no | `si` \| `no` | `no` | default `no` |
| `tipo_renovacion` | no | `sin_renovacion` \| `automatica` \| `con_aviso` \| `manual` | `automatica` | default `sin_renovacion` |
| `aviso_previo_dias` | no | entero | `60` | default `60`; días de aviso contractual |
| `causales_termino` | no | texto | `Incumplimiento grave; mutuo acuerdo` | |
| `archivo_contrato` | no | texto (nombre de archivo) | `2025-03_aseos-del-sur_aseo.pdf` | debe existir en `Contratos/Documentos/` |
| `observaciones` | no | texto | | notas de la migración |

---

## Hoja `Garantias` (opcional)

| Columna | Req | Tipo / valores | Ejemplo |
|---|---|---|---|
| `contrato_codigo_externo` | sí | texto | `SC-1042` |
| `tipo` | sí | `seriedad_oferta` \| `fiel_cumplimiento` \| `anticipo` \| `correcta_ejecucion` \| `otra` | `fiel_cumplimiento` |
| `instrumento` | sí | `boleta_bancaria` \| `poliza_seguro` \| `retencion` \| `pagare` \| `otro` | `boleta_bancaria` |
| `emisor` | no | texto | `Banco Estado` |
| `numero` | no | texto | `0012345` |
| `monto` | sí | número | `1850000` |
| `moneda` | sí | `CLP` \| `UF` \| `USD` \| `EUR` \| `otro` | `CLP` |
| `fecha_emision` | sí | fecha | `2025-03-24` |
| `fecha_vencimiento` | sí | fecha | `2026-04-30` |
| `estado` | no | `vigente` \| `ejecutada` \| `devuelta` \| `reemplazada` | `vigente` |
| `glosa` | no | texto | `Garantiza fiel cumplimiento contrato aseo` |

---

## Hoja `Hitos` (opcional)

| Columna | Req | Tipo / valores | Ejemplo |
|---|---|---|---|
| `contrato_codigo_externo` | sí | texto | `SC-1042` |
| `tipo` | sí | `inicio_ejecucion` \| `entregable` \| `pago` \| `renovacion` \| `termino` \| `revision` \| `otro` | `renovacion` |
| `nombre` | sí | texto | `Aviso de renovación` |
| `fecha_planificada` | sí | fecha | `2026-01-31` |
| `fecha_real` | no | fecha | |
| `estado` | no | `pendiente` \| `cumplido` \| `atrasado` \| `cancelado` | `pendiente` |
| `responsable_email` | no | email | `rgomez@empresa.cl` |
| `notas` | no | texto | |

---

## Hoja `Listas` (solo referencia / validación de datos)

- **linea:** `A`, `B`, `C`
- **estado_contrato:** `ingreso`, `aprobacion_jefatura`, `aprobacion_gerencia`,
  `admisibilidad_1`, `admisibilidad_2`, `elaboracion`, `visacion`, `firma`,
  `integracion`, `vigente`, `terminado`, `aclaraciones`, `descartado`
- **moneda:** `CLP`, `UF`, `USD`, `EUR`, `otro`
- **categoria:** `servicio`, `suministro`, `arriendo`, `obra`, `licencia`, `otro`
- **tipo_renovacion:** `sin_renovacion`, `automatica`, `con_aviso`, `manual`
- **si_no:** `si`, `no`
- **garantia_tipo:** `seriedad_oferta`, `fiel_cumplimiento`, `anticipo`,
  `correcta_ejecucion`, `otra`
- **garantia_instrumento:** `boleta_bancaria`, `poliza_seguro`, `retencion`, `pagare`, `otro`
- **hito_tipo:** `inicio_ejecucion`, `entregable`, `pago`, `renovacion`, `termino`,
  `revision`, `otro`

---

## Validaciones del importador (Etapa 2)

1. Encabezados presentes y con el nombre exacto.
2. Campos obligatorios no vacíos; `linea` y `estado_actual` dentro de las listas.
3. `formato_estandar` obligatorio y existente cuando `linea = B`.
4. `moneda` presente si hay `monto`.
5. `fecha_fin_vigencia` presente cuando corresponde (regla de la columna).
6. Coherencia de fechas: `ingreso ≤ aprobacion ≤ admisibilidad ≤ visacion ≤ firma ≤
   integracion ≤ inicio_vigencia ≤ fin_vigencia` (las que estén informadas).
7. `archivo_contrato`, si se indica, debe existir en `Contratos/Documentos/`.
8. `contrato_codigo_externo` de las hojas Garantías/Hitos debe existir en la hoja Contratos.
9. Filas con error se reportan (fila + motivo) y **no** se importan; el resto sí.
10. Re-importar una fila con `codigo_externo` ya cargado **actualiza** el contrato (no lo
    duplica).

## Comportamiento del importador (Etapa 2)

- Implementado en `app/services/importador.py`. Se invoca con
  `python -m scripts.importar <archivo>` o `POST /importaciones/contratos`
  (`{"archivo": "...", "carpeta": null}`; `carpeta` por defecto `Contratos/Planillas/`).
- **Auto-alta de catálogos:** si `unidad_solicitante`, `contraparte_razon_social` o los
  correos de usuario no existen, se crean automáticamente y se añade una **advertencia**
  al resultado. Los usuarios nuevos reciben un rol tentativo por su columna
  (`solicitante_email`→`unidad_solicitante`, `abogado_email`→`legal`,
  `administrador_email`→`admin_contratos`, `responsable_email`→`tecnica`); **revisar** esos
  roles después de la carga.
- **Trazabilidad:** cada contrato nuevo queda con un único evento "Carga inicial desde
  &lt;archivo&gt;" en su `estado_actual`; el importador no recorre el flujo.
- **Limitación conocida:** re-importar hojas `Garantias`/`Hitos` vuelve a insertar esas
  filas (no tienen llave natural). Para corregir garantías o hitos ya cargados, usar la
  API (`/contratos/{id}/garantias`, `/contratos/{id}/hitos`) en vez de re-importar.
- Resultado: `{creados: [...], actualizados: [...], errores: [{hoja, fila, motivo}],
  advertencias: [...]}`.
