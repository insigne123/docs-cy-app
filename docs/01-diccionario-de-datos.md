# 01 — Diccionario de datos

Modelo lógico del sistema de Contratos y Licitaciones.
Contexto: [`../CLAUDE.md`](../CLAUDE.md) · Plan: [`../ROADMAP.md`](../ROADMAP.md)

Convenciones:
- Toda tabla tiene `id` (PK, autonumérico) salvo que se indique otra cosa.
- Auditoría estándar en tablas principales: `creado_en`, `creado_por_id`,
  `actualizado_en`, `actualizado_por_id`.
- Fechas de negocio: tipo `date`. Marcas de tiempo del sistema: `timestamp`.
- Montos: `decimal(18,2)` + `moneda`.
- "FK → X" significa clave foránea a la tabla X.

---

## 1. `usuario`

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| nombre | texto | sí | |
| email | texto | sí | único; sirve de login |
| rol | enum `rol` | sí | ver enum `rol` |
| unidad_id | FK → unidad | no | unidad organizacional a la que pertenece |
| activo | bool | sí | default `true` |
| password_hash | texto | sí | |
| ultimo_acceso | timestamp | no | |

Un usuario tiene **un** rol principal. Si a futuro se necesitan varios, se pasa a tabla
`usuario_rol`.

---

## 2. `unidad`

Catálogo de áreas organizacionales (para filtrar el dashboard "por área").

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| nombre | texto | sí | único |
| tipo | enum: `solicitante`, `interna` | sí | |
| jefatura_id | FK → usuario | no | jefe que aprueba (rol `jefatura`) |
| activo | bool | sí | |

---

## 3. `contraparte`

Terceros con los que se contrata (proveedores, clientes, mandantes de licitación).

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| razon_social | texto | sí | |
| rut | texto | no | identificador tributario; único si viene informado |
| tipo | enum: `proveedor`, `cliente`, `mandante`, `otro` | sí | |
| contacto_nombre | texto | no | |
| contacto_email | texto | no | |
| contacto_telefono | texto | no | |
| notas | texto | no | |

---

## 4. `contrato`  *(expediente contractual — núcleo del sistema)*

Un solo registro cubre todo el ciclo de vida, desde el ingreso de la solicitud hasta el
término. Muchos campos quedan nulos hasta la etapa que los produce.

### Identificación
| Campo | Tipo | Req | Notas |
|---|---|---|---|
| codigo | texto | sí | único, legible. Formato `CT-AAAA-####`, generado por el sistema |
| codigo_externo | texto | no | código previo del contrato si ya existía (carga inicial) |
| linea | enum: `A_regular`, `B_autogestionado`, `C_licitacion` | sí | |
| objeto | texto | sí | descripción del contrato |
| categoria | enum: `servicio`, `suministro`, `arriendo`, `obra`, `licencia`, `otro` | no | |

### Relaciones
| Campo | Tipo | Req | Notas |
|---|---|---|---|
| unidad_solicitante_id | FK → unidad | sí | |
| solicitante_id | FK → usuario | sí | quién ingresó la solicitud |
| contraparte_id | FK → contraparte | no | puede definirse después del ingreso |
| abogado_id | FK → usuario | no | asignado en Admisibilidad II (rol `legal`) |
| administrador_id | FK → usuario | no | administrador del contrato (designado en Integración) |
| formato_id | FK → formato_estandar | no | **solo Línea B** |
| licitacion_id | FK → licitacion | no | si el contrato proviene de una licitación adjudicada |

### Estado / flujo
| Campo | Tipo | Req | Notas |
|---|---|---|---|
| estado | enum `estado_contrato` | sí | ver [`02-maquina-de-estados.md`](02-maquina-de-estados.md) |
| estado_desde | timestamp | sí | inicio del estado actual (para medir permanencia / SLA) |
| requiere_aprobacion_gerencia | bool | sí | derivado: `monto >= parametro.monto_aprobacion_gerencia` |
| requiere_garantia | bool | sí | default `false`; si `true`, no se permite `firma` sin garantía vigente |

### Montos
| Campo | Tipo | Req | Notas |
|---|---|---|---|
| monto | decimal | no | |
| moneda | enum `moneda` | no | `CLP`, `UF`, `USD`, `EUR`, `otro` |
| monto_referencia_clp | decimal | no | para totalizar el dashboard en una sola moneda |

### Fechas del ciclo
| Campo | Tipo | Notas |
|---|---|---|
| fecha_ingreso | date | obligatoria |
| fecha_aprobacion_jefatura | date | |
| fecha_admisibilidad | date | cierre de Admisibilidad II |
| fecha_visacion | date | |
| fecha_firma | date | |
| fecha_integracion | date | |

### Vigencia
| Campo | Tipo | Req | Notas |
|---|---|---|---|
| fecha_inicio_vigencia | date | no | |
| fecha_fin_vigencia | date | no | obligatoria para pasar a `vigente` salvo `vigencia_indefinida` |
| vigencia_indefinida | bool | sí | default `false` |
| tipo_renovacion | enum: `sin_renovacion`, `automatica`, `con_aviso`, `manual` | sí | default `sin_renovacion` |
| aviso_previo_dias | int | sí | default `60`. Días de aviso contractual para renovar/terminar |
| causales_termino | texto | no | |

### Cierre
| Campo | Tipo | Notas |
|---|---|---|
| motivo_descarte | texto | obligatorio si `estado = descartado` |
| fecha_cierre | date | fecha de término o descarte |

---

## 5. `evento_estado`  *(trazabilidad — inmutable)*

Una fila por cada cambio de estado. **No se edita ni se borra.**

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| entidad_tipo | enum: `contrato`, `licitacion` | sí | |
| entidad_id | int | sí | FK lógica a `contrato` o `licitacion` |
| estado_origen | enum | no | nulo en el primer evento |
| estado_destino | enum | sí | |
| fecha | timestamp | sí | |
| usuario_id | FK → usuario | sí | quién ejecutó la transición |
| rol_actor | enum `rol` | sí | rol con el que actuó |
| comentario | texto | no | |
| retorno_a | enum | no | al entrar a `aclaraciones`: estado al que se volverá |
| documento_id | FK → documento | no | respaldo de la transición (acta, aprobación, etc.) |

---

## 6. `garantia`

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| entidad_tipo | enum: `contrato`, `licitacion` | sí | `licitacion` para garantía de seriedad de oferta |
| entidad_id | int | sí | |
| tipo | enum: `seriedad_oferta`, `fiel_cumplimiento`, `anticipo`, `correcta_ejecucion`, `otra` | sí | |
| instrumento | enum: `boleta_bancaria`, `poliza_seguro`, `retencion`, `pagare`, `otro` | sí | |
| emisor | texto | no | banco / aseguradora |
| numero | texto | no | folio del instrumento |
| monto | decimal | sí | |
| moneda | enum `moneda` | sí | |
| fecha_emision | date | sí | |
| fecha_vencimiento | date | sí | alimenta alertas 90/60/30 |
| estado | enum: `vigente`, `por_vencer`, `vencida`, `ejecutada`, `devuelta`, `reemplazada` | sí | `por_vencer`/`vencida` se recalculan a diario |
| glosa | texto | no | |
| documento_id | FK → documento | no | |

---

## 7. `multa`

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| contrato_id | FK → contrato | sí | |
| descripcion | texto | sí | |
| monto | decimal | sí | |
| moneda | enum `moneda` | sí | |
| fecha_aplicacion | date | sí | |
| estado | enum: `propuesta`, `aplicada`, `en_disputa`, `pagada`, `condonada` | sí | |
| documento_id | FK → documento | no | |

---

## 8. `hito`

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| contrato_id | FK → contrato | sí | |
| tipo | enum: `inicio_ejecucion`, `entregable`, `pago`, `renovacion`, `termino`, `revision`, `otro` | sí | |
| nombre | texto | sí | |
| fecha_planificada | date | sí | |
| fecha_real | date | no | |
| estado | enum: `pendiente`, `cumplido`, `atrasado`, `cancelado` | sí | `atrasado` se recalcula a diario |
| responsable_id | FK → usuario | no | |
| notas | texto | no | |

---

## 9. `documento`

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| entidad_tipo | enum: `contrato`, `licitacion` | sí | |
| entidad_id | int | sí | |
| tipo | enum: `solicitud`, `antecedente`, `borrador`, `contrato_firmado`, `anexo`, `garantia`, `bases`, `oferta_tecnica`, `oferta_economica`, `informe_riesgos`, `acta`, `otro` | sí | |
| nombre_archivo | texto | sí | |
| ruta | texto | sí | ubicación en el almacén de archivos (`Contratos/Documentos/…` o storage del servidor) |
| version | int | sí | default `1` |
| hash_sha256 | texto | no | integridad / verificación de formato (Línea B) |
| cargado_por_id | FK → usuario | sí | |
| cargado_en | timestamp | sí | |

---

## 10. `formato_estandar`  *(Línea B)*

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| nombre | texto | sí | único junto con `version` |
| version | int | sí | |
| vigente | bool | sí | solo un `vigente = true` por `nombre` |
| aprobado_por | texto | sí | ej. "Fiscalía", "Área Legal" |
| fecha_aprobacion | date | sí | |
| campos_variables | json | sí | lista de campos que el solicitante puede completar |
| ruta_plantilla | texto | sí | archivo base del formato |
| checksum_base | texto | sí | hash del clausulado estándar; se compara para detectar modificación |

---

## 11. `licitacion`

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| codigo | texto | sí | único, `LIC-AAAA-####` |
| codigo_externo | texto | no | ID del portal / mandante |
| objeto | texto | sí | |
| mandante | texto | no | organismo/empresa convocante (o `contraparte_id`) |
| contraparte_id | FK → contraparte | no | |
| unidad_solicitante_id | FK → unidad | sí | |
| fase | enum: `pre_adjudicacion`, `formalizacion`, `cerrada` | sí | |
| estado | enum `estado_licitacion` | sí | ver [`02-maquina-de-estados.md`](02-maquina-de-estados.md) |
| fecha_publicacion_bases | date | no | |
| fecha_ingreso | date | sí | |
| fecha_cierre_ofertas | date | no | |
| fecha_apertura | date | no | |
| presupuesto_referencia | decimal | no | |
| moneda | enum `moneda` | no | |
| resultado | enum: `en_proceso`, `adjudicado`, `no_adjudicado`, `desierto`, `desistido` | sí | default `en_proceso` |
| fecha_resultado | date | no | |
| contrato_id | FK → contrato | no | contrato creado al adjudicar |
| informe_riesgos_id | FK → documento | no | Informe de Riesgos y Validación Final |
| analisis_interno | texto | no | mejora continua cuando `no_adjudicado` |

---

## 12. `parametro`  *(configuración del sistema)*

| clave | valor por defecto | descripción |
|---|---|---|
| `alerta_umbrales_dias` | `90,60,30` | niveles de alerta antes de vencimiento/renovación |
| `monto_aprobacion_gerencia_clp` | `50000000` | monto desde el cual se exige aprobación de Gerencia |
| `aclaraciones_dias_alerta` | `10` | días en `aclaraciones` tras los cuales se marca "solicitud estancada" |
| `moneda_base` | `CLP` | moneda para totalizar el dashboard |
| `dashboard_agrupacion_default` | `vencimiento` | criterio inicial del selector (ingreso/firma/vencimiento) |

---

## 13. Alertas (calculadas, no se almacenan salvo cuando se "resuelven")

Tipos: `contrato_por_vencer`, `contrato_vencido`, `renovacion_proxima`,
`garantia_por_vencer`, `garantia_vencida`, `hito_atrasado`,
`solicitud_estancada_aclaraciones`, `sin_administrador`, `sin_garantia_previo_firma`.

Nivel según días restantes a la fecha de referencia: `informativa` (≤90), `atencion` (≤60),
`urgente` (≤30), `critica` (vencido, días < 0).

Tabla opcional `alerta_resuelta` (`tipo`, `entidad_tipo`, `entidad_id`, `fecha_referencia`,
`resuelta_por_id`, `resuelta_en`, `nota`) para silenciar una alerta ya gestionada.

---

## 14. Enums

| Enum | Valores |
|---|---|
| `rol` | `unidad_solicitante`, `jefatura`, `legal`, `admin_licitaciones`, `financiera`, `tecnica`, `gerencia`, `admin_contratos`, `admin_sistema` |
| `moneda` | `CLP`, `UF`, `USD`, `EUR`, `otro` |
| `estado_contrato` | `ingreso`, `aprobacion_jefatura`, `aprobacion_gerencia`, `admisibilidad_1`, `admisibilidad_2`, `elaboracion`, `visacion`, `firma`, `integracion`, `vigente`, `terminado`, `aclaraciones`, `descartado`, `formalizacion_ajuste`, `constitucion_garantias` |
| `estado_licitacion` | `ingreso_antecedentes`, `examen_admisibilidad`, `revision_bases`, `preparacion_oferta`, `presentacion_oferta`, `evaluacion_resultado`, `adjudicada`, `no_adjudicada`, `desierta`, `desistida`, `descartado` |

---

## 15. Relaciones (resumen)

```
unidad 1─* usuario
unidad 1─* contrato            (unidad_solicitante)
usuario 1─* contrato           (solicitante / abogado / administrador)
contraparte 1─* contrato
contraparte 1─* licitacion
formato_estandar 1─* contrato  (solo Línea B)
licitacion 1─0..1 contrato     (al adjudicar)
contrato 1─* evento_estado
contrato 1─* garantia / multa / hito / documento
licitacion 1─* evento_estado / garantia (seriedad) / documento
```
