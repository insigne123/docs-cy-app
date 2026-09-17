# 05 — Despliegue en producción (app online + base de datos en la nube)

Objetivo: que varias personas usen la aplicación desde internet, con una sola base de
datos PostgreSQL compartida. No usa Supabase ni Firebase — el sistema ya tiene su propio
backend, base de datos y autenticación (ver `CLAUDE.md`); esas plataformas reemplazarían
justamente eso, no lo complementan.

## Qué ya quedó listo en el código

- **`DATABASE_URL` acepta Postgres directamente**, incluida la forma `postgres://` que
  entregan Railway/Render/Heroku (se normaliza sola en `app/config.py`).
- **Migraciones con Alembic** (`alembic/`) en vez de crear las tablas a mano — necesario
  para una base compartida real. Ya generada y probada la migración inicial
  (`alembic/versions/..._esquema_inicial.py`): crea las 12 tablas del esquema.
- **Toda la escritura y los catálogos quedan protegidos** cuando `AUTH_REQUIRED=true`
  (antes solo protegía contratos/licitaciones; ahora también `/usuarios`, `/alertas`,
  `/metricas`, `/panel.json`, etc.).
- **`scripts/crear_admin.py`**: crea el primer usuario con clave directo en la base
  (necesario porque, con auth activa, la propia API para crear usuarios ya pide token).
- **Cookie de sesión `Secure`** automática cuando `AUTH_REQUIRED=true` (asume HTTPS).
- **`Procfile`** (`alembic upgrade head && uvicorn ...`) y **`render.yaml`** (blueprint)
  para desplegar con un comando o con un clic.
- Repositorio **git inicializado** con un commit del estado actual.

## Variables de entorno de producción

| Variable | Valor |
|---|---|
| `DATABASE_URL` | La que entregue el proveedor de Postgres (Railway/Render la inyectan solas) |
| `AUTH_REQUIRED` | `true` |
| `SECRET_KEY` | Una cadena larga y aleatoria — **no** la de `.env.example`. Generarla con `python -c "import secrets; print(secrets.token_hex(32))"` |

---

## Camino A — Railway (recomendado: sin necesitar GitHub)

Railway despliega directo desde tu carpeta local con su CLI.

1. **Instalar la CLI** (PowerShell):
   ```bash
   winget install -e --id Railway.railway
   ```
   Si winget no la reconoce, alternativa vía npm: `npm i -g @railway/cli` (requiere Node).

2. **Iniciar sesión** (abre el navegador; entras tú con tu cuenta, yo no participo en esto):
   ```bash
   railway login
   ```

3. **Crear el proyecto** en la carpeta del repo:
   ```bash
   railway init
   ```

4. **Agregar una base PostgreSQL** al proyecto (desde el dashboard que abre `railway open`,
   o `railway add` y elegir "PostgreSQL" en el menú). Railway inyecta `DATABASE_URL`
   automáticamente al servicio.

5. **Configurar las variables**:
   ```bash
   railway variables --set AUTH_REQUIRED=true --set SECRET_KEY=<pega-aqui-tu-clave-generada>
   ```

6. **Desplegar**:
   ```bash
   railway up
   ```
   Railway detecta Python (por `requirements.txt`) y usa el `Procfile` (corre las
   migraciones y luego levanta uvicorn).

7. **Generar un dominio público** y abrirlo:
   ```bash
   railway domain
   railway open
   ```

8. **Crear el primer usuario administrador** (una vez, contra la base ya desplegada):
   ```bash
   railway run python -m scripts.crear_admin admin@tuempresa.cl "una-clave-larga-y-segura" "Nombre Admin"
   ```

9. Entra a `https://<tu-dominio>/login` con ese email/clave.

---

## Camino B — Render (blueprint desde GitHub)

Si prefieres administrar todo desde un panel web y ya usas GitHub.

1. **Crear el repositorio en GitHub** (tú, desde tu cuenta) y subir el código:
   ```bash
   git remote add origin https://github.com/<tu-usuario>/contratos-licitaciones.git
   git branch -M main
   git push -u origin main
   ```

2. **Crear cuenta en [render.com](https://render.com)** (gratis) y conectarla a tu GitHub.

3. **New → Blueprint**, elegir el repositorio. Render lee `render.yaml` del proyecto y
   propone crear la base `contratos-db` (Postgres) y el servicio `contratos-app` juntos,
   con `SECRET_KEY` autogenerada y `DATABASE_URL` ya conectada. Revisar y **Apply**.

4. Cuando el servicio quede "Live", abrir su URL (Render te la muestra en el dashboard).

5. **Crear el primer usuario administrador** desde el **Shell** del servicio (pestaña
   "Shell" en el dashboard de Render):
   ```bash
   python -m scripts.crear_admin admin@tuempresa.cl "una-clave-larga-y-segura" "Nombre Admin"
   ```

6. Entra a `https://<tu-servicio>.onrender.com/login`.

> El plan gratuito de Render "duerme" el servicio tras 15 min sin tráfico (la primera
> visita tras dormir tarda unos segundos en responder) y la base gratuita expira a los
> 90 días. Para uso real de varias personas conviene pasar al plan pago cuando se
> confirme que el sistema funciona.

---

## Después de desplegar

- **Cargar los datos existentes**: usar `/panel` → sección de importación, o
  `POST /importaciones/contratos` con la planilla ya en el servidor (o extenderlo para
  subir el archivo por HTTP — hoy el importador lee desde una carpeta del servidor).
- **Crear las unidades, contrapartes, formatos y usuarios reales** por la API (`/docs`)
  con el token del administrador.
- **Respaldo de la base en la nube**: Railway y Render ofrecen respaldos automáticos de
  Postgres en sus planes pagos; para un respaldo manual, `pg_dump "$DATABASE_URL" > backup.sql`
  desde cualquier máquina con `psql`/`pg_dump` instalado (o `railway run pg_dump ...`).
- **Actualizar la app**: cada `railway up` (o cada `git push` a la rama conectada en
  Render) vuelve a desplegar; las migraciones nuevas se aplican solas al iniciar
  (`alembic upgrade head` corre en cada arranque, sin efecto si no hay cambios).

## Seguridad — qué revisar antes de compartir el enlace

- `SECRET_KEY` real y distinta a la de `.env.example`.
- `AUTH_REQUIRED=true` en el entorno de producción.
- Usuarios con contraseñas propias (no los "provisionales" que crea el importador).
- El sistema no distingue roles por endpoint todavía: **cualquier usuario autenticado
  puede hacer cualquier operación de escritura**. Si eso es un problema para tu caso de
  uso, es la extensión pendiente más importante (control de acceso por rol, Etapa 7).
- No hay límite de intentos de login (fuerza bruta) ni recuperación de clave — para una
  primera versión interna es aceptable; para exposición pública amplia, conviene sumarlo.
