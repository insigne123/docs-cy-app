# Operación docs-cy (Contratos y Licitaciones)

Todo se hace en el navegador, sin descargar nada.

## URLs

- App pública: https://docs-cy.web.app (`/panel`, `/login`, `/health`)
- Admin inicial: `admin@yago.cl` (clave en custodia del equipo)
- Cloud Run: proyecto `yago-axis-prod`, servicio `docs-cy2`, región `us-central1`
- Base de datos: Supabase (dashboard en supabase.com)

## Cómo cambiar la app y publicar

1. Abre el repo en el navegador: `github.dev/<owner>/docs-cy-app` (edición rápida)
   o crea un Codespace para sesiones largas.
2. Edita, haz commit a una rama y abre un Pull Request (corre las pruebas solas).
3. Al hacer merge a `main`, GitHub Actions corre pruebas y despliega solo.
   Verifica en la pestaña Actions y luego en https://docs-cy.web.app/health.

## Migraciones de base de datos

El contenedor ejecuta `alembic upgrade head` al partir: cada deploy aplica
migraciones nuevas automáticamente. Para cambios de datos o crear usuarios,
usa Supabase (SQL editor / Table editor) o agrega scripts en `scripts/`.

## Secretos (no van al repo)

- GitHub → Settings → Secrets → Actions: `APP_SECRET_KEY`,
  `PROD_DATABASE_URL`. (Sin llaves: el deploy usa identidad federada
  `github-pool` → cuenta `docs-cy-deployer`.)
- Nunca subas `.env` (está en `.gitignore`).

## Volver atrás

Actions → corre de nuevo un deploy anterior, o en Cloud Run → revisiones →
redirige el tráfico a la revisión estable.
