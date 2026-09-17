# Carpeta "Contratos" — zona de carga

Aquí se depositan los contratos **actuales** y los **futuros**. El sistema (a partir de
la Etapa 2 del [ROADMAP](../ROADMAP.md)) leerá esta carpeta para la carga inicial masiva
y para incorporaciones posteriores.

## Estructura

- **`Planillas/`** — Archivos Excel o CSV con los **datos** de los contratos
  (una fila por contrato) para la importación masiva.
  El formato exacto de columnas se define en la Etapa 0 y se dejará una plantilla
  de ejemplo en `Planillas/_plantilla.xlsx`.

- **`Documentos/`** — Los archivos de los contratos en sí (PDF / Word) y sus anexos.
  Sugerencia de nombre: `AAAA-MM_contraparte_objeto.pdf`.

## Reglas provisionales (a confirmar en Etapa 0)

- Cada contrato de `Planillas/` debe poder enlazarse con su archivo en `Documentos/`
  mediante un identificador o el nombre de archivo.
- No borrar planillas ya importadas: moverlas a `Planillas/_procesadas/`.
- Datos mínimos por contrato: contraparte, objeto, línea (A/B/C), unidad solicitante,
  monto, moneda, fecha de firma, inicio y fin de vigencia, tipo de renovación,
  administrador, estado actual.
