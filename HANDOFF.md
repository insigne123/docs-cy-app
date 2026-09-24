# HANDOFF — Leer esto primero en el nuevo workspace

Punto de partida único para retomar el proyecto en otro espacio de trabajo / otra sesión
de Claude, sin depender de la memoria de la conversación anterior. Todo lo demás
(`CLAUDE.md`, `ROADMAP.md`, `docs/`) está versionado en este mismo repo git.

## Qué es esto

Sistema de gestión de **Contratos y Licitaciones** (FastAPI + SQLAlchemy + Postgres/SQLite
+ panel web Jinja2), construido de cero a partir de la documentación de proceso del
negocio. Contexto completo del proceso: [`CLAUDE.md`](CLAUDE.md). Plan por etapas con
entregable verificable en cada una: [`ROADMAP.md`](ROADMAP.md).

## Estado al momento de este traspaso (2026-09-24)

- **Etapas 0 a 6 completas y verificadas. Etapa 7 parcial. Etapa 8 (despliegue) con el
  código listo**, a la espera de que el usuario cree las cuentas de Supabase y Google
  Cloud/Firebase (ver más abajo — es la siguiente acción pendiente).
- **68/68 pruebas pasan.**
- **4 commits en git**, working tree limpio, sin remoto configurado todavía.
- No hay archivo `.env` ni secretos en el repo (el `.gitignore` los excluye).

## Cómo moverlo a otro workspace

Este repo ya tiene historial git completo. Dos formas de llevarlo:

**A) Copiar la carpeta tal cual** — `C:\Users\Cyarur\Downloads\Nuevo proyecto Contratos`
completa (incluye `.git/`) a la nueva ubicación/máquina. Es la más simple si es el mismo
usuario/equipo o vía una unidad compartida.

**B) Bundle de git** (portable, un solo archivo, preserva todo el historial) — te lo dejo
en `contratos-licitaciones.bundle` junto a este documento. En el workspace nuevo:
```bash
git clone contratos-licitaciones.bundle "Nuevo proyecto Contratos"
cd "Nuevo proyecto Contratos"
```

Lo que **no** viaja con ninguna de las dos formas (vive fuera del repo, en este equipo):
- La **memoria persistente** de Claude para este proyecto:
  `C:\Users\Cyarur\.claude\projects\C--Users-Cyarur-Downloads-Nuevo-proyecto-Contratos\memory\`.
  No es necesaria — todo lo que contiene ya está reflejado en `CLAUDE.md`/`ROADMAP.md`/este
  archivo — pero si quieres llevarla, cópiala a mano al equivalente del workspace nuevo.
- Cualquier `.env` local con secretos reales (no existe ninguno en este momento).

## Cómo verificar que todo sigue funcionando ahí

Este equipo **no tiene Python nativo** (solo `uv`, instalado vía winget). Si el workspace
nuevo tampoco lo tiene, repite eso; si tiene Python 3.10+, usa `pip` normal
(ver [`README_DEV.md`](README_DEV.md), sección "Opción 2").

```bash
winget install --id=astral-sh.uv -e
uv run --no-project --python 3.12 --with-requirements requirements-dev.txt pytest
```

Debe imprimir `68 passed`. Demo funcional sin base real:
```bash
uv run --no-project --python 3.12 --with-requirements requirements.txt python -m scripts.demo_flujos
```

Levantar la app localmente: `uvicorn app.main:app --reload` → `http://127.0.0.1:8000/panel`.

## Qué falta — próximo paso pendiente

El usuario pidió explícitamente desplegar con **Supabase (Postgres) + Firebase
(Hosting) / Cloud Run**. El código ya está adaptado y probado; falta que el usuario:

1. Cree el proyecto en Supabase y copie el `DATABASE_URL` del *connection pooler*.
2. Cree/use un proyecto de Google Cloud y despliegue con `gcloud run deploy --source .`
3. Instale Node.js + `firebase-tools` y publique con `firebase deploy --only hosting`.

Guía completa paso a paso, con los comandos exactos: **[`docs/06-despliegue-supabase-firebase.md`](docs/06-despliegue-supabase-firebase.md)**.
(Alternativa evaluada primero, sigue disponible: Railway/Render en `docs/05-despliegue-produccion.md`.)

Herramientas que ya quedaron instaladas en **este** equipo (revisar si el workspace nuevo
es la misma máquina o si hay que reinstalarlas ahí): `git`
(`%LOCALAPPDATA%\Programs\Git\cmd\git.exe`, agregado al PATH de usuario), `uv`
(`%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe`), Google Cloud SDK. **Node.js quedó
pendiente** (el instalador MSI de winget falló por un bloqueo de UAC) — instalarlo con
`winget install -e --id OpenJS.NodeJS.LTS` o desde nodejs.org.

## Gotchas que ya se resolvieron una vez (no repetirlos)

- **No editar los `.md` con acentos usando `Get-Content -Raw` + `Set-Content -Encoding
  utf8` en PowerShell 5.1** — corrompe el archivo por doble codificación UTF-8. Usar
  `[System.IO.File]::ReadAllText/WriteAllBytes` con UTF-8 explícito, o el editor de
  archivos normal (Read/Edit), no PowerShell, para tocar texto con tildes.
- Las variables de entorno de PowerShell (`$env:...`) **no persisten entre llamadas** de
  la herramienta de shell — hay que fijarlas y usarlas dentro de la misma invocación.
- El importador de planillas auto-crea unidades/contrapartes/usuarios faltantes (con
  advertencia) — es intencional, no un bug.

## Índice de documentación del repo

| Archivo | Contenido |
|---|---|
| `CLAUDE.md` | Proceso de negocio completo (roles, líneas A/B/C, estados, WorkGes) + estado del proyecto etapa por etapa |
| `ROADMAP.md` | Plan por etapas con entregable verificable en cada una (0 a 8) |
| `README_DEV.md` | Cómo instalar, correr pruebas, levantar la app, estructura del código |
| `docs/01-diccionario-de-datos.md` | Modelo de datos completo |
| `docs/02-maquina-de-estados.md` | Estados y transiciones de las 3 líneas |
| `docs/03-plantilla-carga-contratos.md` | Formato de la planilla de importación |
| `docs/04-manual-de-uso.md` | Manual de uso funcional del sistema |
| `docs/05-despliegue-produccion.md` | Despliegue alternativo: Railway / Render |
| `docs/06-despliegue-supabase-firebase.md` | **Despliegue elegido**: Supabase + Firebase/Cloud Run |
