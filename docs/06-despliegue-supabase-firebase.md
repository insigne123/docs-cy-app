# 06 — Despliegue con Supabase + Firebase

Este es el camino elegido: **Supabase como base de datos PostgreSQL en la nube** +
**Firebase Hosting** como URL pública, apuntando a un contenedor en **Cloud Run** que
corre esta misma aplicación (FastAPI). No se reescribió el backend para usar el SDK de
Supabase ni el de Firebase — ambos se usan como infraestructura (base de datos y
hosting/CDN), que es exactamente lo que son.

## Por qué Cloud Run y no solo Firebase Hosting

Firebase Hosting sirve **archivos estáticos** o reenvía (`rewrite`) tráfico a un backend
— no ejecuta un proceso Python por sí solo. Para que `firebase.json` pueda reenviar todo
el tráfico a esta app, la app necesita correr en **Cloud Run** (un contenedor). Ya dejé
todo listo para eso: `Dockerfile`, `firebase.json` (con el rewrite) y `.firebaserc`.

---

## Resumen de lo que ya preparé en el código

- **`app/config.py`**: `DATABASE_URL` acepta el formato de Supabase (`postgres://…`),
  lo normaliza al driver `psycopg`, y **exige SSL automáticamente** para cualquier
  Postgres remoto (Supabase lo requiere).
- **`app/database.py`**: `prepare_threshold=None` en la conexión — necesario si usas el
  *pooler* de Supabase (Supavisor/pgbouncer en modo *transaction*, puerto 6543).
- **`Dockerfile`**: aplica las migraciones (`alembic upgrade head`) y levanta la app;
  Cloud Run puede construirlo sin que tengas Docker instalado localmente.
- **`firebase.json` / `.firebaserc`**: Hosting reenvía *todo* el tráfico al servicio de
  Cloud Run `contratos-app` en `us-central1` (cambia la región si usas otra).
- **`scripts/crear_admin.py`**: como Supabase es accesible directamente por internet, este
  y los demás scripts (`init_db`, `importar`, `reporte`, `alembic`) se ejecutan **desde tu
  propia máquina** apuntando a la base de Supabase — no hace falta entrar al contenedor.
- Pruebas: `tests/test_config.py` cubre la normalización de la URL. **68/68 pruebas pasan.**

---

## Paso 1 — Crear el proyecto en Supabase (lo haces tú)

1. Entra a [supabase.com](https://supabase.com) y crea una cuenta / proyecto nuevo
   (elige una región cercana a donde estará Cloud Run, ej. `us-central1` → región de
   EE.UU. en Supabase).
2. Guarda la **contraseña de la base de datos** que te pide al crear el proyecto.
3. En **Project Settings → Database → Connection string**, copia la cadena en modo
   **URI**. Para producción con varias instancias, usa la del **Connection pooler**
   (modo *Transaction*, puerto `6543`) — evita agotar las conexiones. Se ve así:
   ```
   postgresql://postgres.xxxxxxxxxxxx:[TU-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
4. Prueba la conexión y crea el esquema **desde tu máquina**:
   ```bash
   $env:DATABASE_URL = "postgresql://postgres.xxxx:TU-PASSWORD@....pooler.supabase.com:6543/postgres"
   uv run --no-project --python 3.12 --with-requirements requirements-dev.txt alembic upgrade head
   ```
   Debe imprimir `Running upgrade -> ..., esquema inicial`. Verifica en Supabase
   (**Table Editor**) que aparecieron las 12 tablas.
5. Crea el primer usuario administrador (misma máquina, mismo `DATABASE_URL`):
   ```bash
   uv run --no-project --python 3.12 --with-requirements requirements.txt python -m scripts.crear_admin admin@tuempresa.cl "clave-larga-y-segura" "Tu Nombre"
   ```

## Paso 2 — Desplegar la app en Cloud Run (lo haces tú; yo dejé el Dockerfile listo)

Necesitas una cuenta de **Google Cloud** (el mismo login de Firebase sirve). El SDK
(`gcloud`) ya quedó instalado en este equipo.

1. Iniciar sesión y elegir/crear el proyecto:
   ```bash
   gcloud auth login
   gcloud projects create tu-proyecto-contratos --set-as-default
   # o, si ya tienes uno: gcloud config set project tu-proyecto-contratos
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com
   ```

2. Generar una `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Desplegar directamente desde el código fuente (Cloud Build construye el `Dockerfile`
   por ti — no necesitas Docker instalado):
   ```bash
   gcloud run deploy contratos-app `
     --source . `
     --region us-central1 `
     --allow-unauthenticated `
     --set-env-vars AUTH_REQUIRED=true `
     --set-env-vars SECRET_KEY=<pega-la-clave-generada> `
     --set-env-vars DATABASE_URL="postgresql://postgres.xxxx:TU-PASSWORD@....pooler.supabase.com:6543/postgres"
   ```
   (En PowerShell, el backtick `` ` `` continúa la línea; también puedes escribir el
   comando en una sola línea.)

4. Al terminar, `gcloud` imprime una URL tipo
   `https://contratos-app-xxxxx-uc.a.run.app` — pruébala: `/health` debe responder
   `{"status":"ok",...}` y `/panel/` debe pedir ingreso (login).

> `--allow-unauthenticated` es necesario para que el público llegue a la app (el control
> de acceso lo hace **nuestra** autenticación, no la de Cloud Run).

## Paso 3 — Publicarlo con Firebase Hosting (lo haces tú)

1. Instalar Node.js (necesario para la CLI de Firebase) si no lo tienes, y la CLI:
   ```bash
   winget install -e --id OpenJS.NodeJS.LTS
   npm install -g firebase-tools
   ```
2. Iniciar sesión y conectar el proyecto (el mismo de Cloud Run):
   ```bash
   firebase login
   firebase use --add
   ```
   Elige el proyecto de Google Cloud del Paso 2; te pedirá un alias, usa `default`.
   Esto actualiza `.firebaserc` (reemplaza `TU-PROYECTO-FIREBASE` por el real).
3. Ajustar en `firebase.json` la `region` si desplegaste Cloud Run en otra distinta de
   `us-central1`.
4. Publicar:
   ```bash
   firebase deploy --only hosting
   ```
5. Firebase entrega una URL `https://tu-proyecto.web.app` — todo el tráfico se reenvía a
   Cloud Run. Ese es el enlace para compartir con el equipo.

*(Opcional)* Dominio propio: en la consola de Firebase → Hosting → "Agregar dominio
personalizado", y sigue las instrucciones de DNS.

---

## Actualizar la app más adelante

Cada cambio de código:
```bash
gcloud run deploy contratos-app --source . --region us-central1
```
No hace falta volver a tocar Firebase Hosting (el rewrite sigue apuntando al mismo
servicio). Las migraciones nuevas de Alembic se aplican solas al iniciar el contenedor.

## Seguridad — repaso antes de compartir el enlace

- `SECRET_KEY` real (no la de ejemplo) y `AUTH_REQUIRED=true` — ya quedaron en el comando
  de despliegue del Paso 2.
- Usa la contraseña de base de datos de Supabase como un secreto real: no la subas al
  repo (no está en ningún archivo versionado; solo vive en la variable de entorno de
  Cloud Run y en tu terminal al ejecutar scripts).
- Mismo pendiente que en `docs/05`: el control de acceso hoy es "autenticado sí/no", sin
  roles finos por endpoint.
- Supabase Free y Cloud Run Free tienen límites (conexiones, cold starts, cuota mensual);
  si el uso crece, revisar los planes pagos de cada uno.
