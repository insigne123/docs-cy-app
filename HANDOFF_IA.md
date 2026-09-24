# HANDOFF para la IA operadora — docs-cy (Contratos y Licitaciones)

Guía para continuar el desarrollo y despliegue de esta app. Léeme primero.

## 1. Qué es y dónde vive

- App: FastAPI + SQLAlchemy + Jinja2 (panel web), Python 3.12.
- Repo: https://github.com/insigne123/docs-cy-app (rama `main`).
- Producción: https://docs-cy.web.app → Firebase Hosting (sitio `docs-cy`,
  proyecto `yago-axis-prod`) → rewrite `**` → Cloud Run `docs-cy2`
  (`us-central1`, proyecto `yago-axis-prod`).
- Base de datos: Supabase Postgres (pooler, puerto 6543). Las tablas ya existen;
  el contenedor corre `alembic upgrade head` al partir (migraciones automáticas).
- Admin inicial: `admin@yago.cl` (la clave la tiene el equipo, no está en el repo).

## 2. Flujo de trabajo (la otra persona no puede descargar nada: todo en navegador)

1. Editar en `github.dev/insigne123/docs-cy-app` o en un Codespace.
2. Commit a `main` (o PR: las pruebas corren solas).
3. GitHub Actions (`CI + Deploy docs-cy`) corre `pytest`, construye la imagen,
   la sube a Artifact Registry y despliega a Cloud Run. Incluye chequeo de
   `/health` al final. Ver en pestaña Actions.
4. No tocar a mano Cloud Run/Hosting salvo emergencia (ver §6).

## 3. CI/CD — piezas

- Workflow: `.github/workflows/deploy.yml`.
- Auth GCP sin llaves: Workload Identity Federation, pool `github-pool`,
  provider `github-provider`, cuenta `docs-cy-deployer@yago-axis-prod.iam.gserviceaccount.com`
  (roles: `run.admin`, `artifactregistry.writer`, `iam.serviceAccountUser`,
  `cloudbuild.builds.editor`, `storage.objectAdmin`, `serviceusage.serviceUsageConsumer`).
- Secrets del repo (Settings → Secrets → Actions): `APP_SECRET_KEY`,
  `PROD_DATABASE_URL` (URL-encoded: `#`→`%23`, `@`→`%40`, `%`→`%25`).
- Build: `docker build/push` en el runner (NO `gcloud builds submit`: el bucket
  de staging bloquea a la cuenta por política de la org).
- Deploy fija además la anotación
  `run.googleapis.com/invoker-iam-disabled=true` (ver §5).

## 4. Reglas del código (causas de incidentes ya resueltos — no revertir)

1. Cookie de sesión se llama `__session` (`app/api/deps.py::COOKIE_SESION`).
   Firebase Hosting elimina cualquier otra cookie hacia Cloud Run.
2. Emails siempre `strip().lower()` al buscar y al crear
   (`routes.py::login_submit`, `routers/auth.py::login`,
   `routers/catalogos.py::crear_usuario`, `importador.py::_usuario`,
   `scripts/crear_admin.py`).
3. `set_cookie` con `path="/"`, `max_age=8*3600`, `Secure` en prod;
   `delete_cookie` con los mismos atributos.
4. Respuestas autenticadas y redirect de login con
   `Cache-Control: private, no-store` (el CDN de Hosting si no sirve páginas viejas).
5. `ProxyHeadersMiddleware(trusted_hosts="*")` en `create_app` (esquema real https).
6. `create_app` falla si `AUTH_REQUIRED=true` con la `SECRET_KEY` de ejemplo.
7. `GET /panel.json` sin sesión → `401 JSON` (no redirect); login web rechaza
   inactivos igual que la API.
8. `alembic/env.py` escapa `%` como `%%` al fijar `sqlalchemy.url`: las claves de
   Supabase con `%` rompen el ConfigParser si no.
9. Nunca commitear `.env` ni secretos (ver `.gitignore`). Las pruebas son 69 y
   deben seguir verdes: `pip install -r requirements-dev.txt && pytest -q`.

## 5. Restricciones de la organización (Google Cloud)

- `iam.allowedPolicyMemberDomains`: prohibido `allUsers` en IAM (error
  "do not belong to a permitted customer"). Cloud Run es privado; lo público
  se expone vía Firebase Hosting + `invoker-iam-disabled=true` en el servicio
  (mismo patrón que el servicio `axisproxy` de este proyecto).
- `iam.disableServiceAccountKeyCreation`: prohibidas las llaves de SA; usar WIF.
- No borrar ni modificar el sitio Hosting `yago-axis-prod` (sirve a AXIS) ni
  nada del proyecto `automata-ai` (sirve a `yago.cl`).

## 6. Emergencia / rollback

- Cloud Run → servicio `docs-cy2` → revisiones → redirigir tráfico a la anterior.
- Re-ejecutar un workflow anterior desde Actions también republica esa imagen.
- Logs: Cloud Logging, `resource.type=cloud_run_revision`,
  `service_name=docs-cy2`. Los 403 de Hosting sin log en Run = IAM/rewrites.

## 7. Pendiente conocido (opcional)

- `yago.cl/docs-cy`: requiere agregar un rewrite en la app Next.js de `yago.cl`
  (proyecto `automata-ai`, backend `studio`, solo editable en Firebase Studio):
  `/docs-cy` → `https://docs-cy.web.app/panel`,
  `/docs-cy/:path*` → `https://docs-cy.web.app/:path*`.
