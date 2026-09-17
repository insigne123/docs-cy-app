# Imagen para Cloud Run (detrás de Firebase Hosting) o cualquier otro host de contenedores.
# Build local opcional: docker build -t contratos-app .
# Cloud Run puede construir esta imagen directo desde el código fuente sin Docker local:
#   gcloud run deploy --source .
FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema mínimas para psycopg[binary] y fpdf2 (ninguna extra requerida,
# pero libpq-dev evita sorpresas si algún día se cambia a psycopg sin binarios).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run inyecta PORT (por defecto 8080) y espera que el contenedor escuche ahí.
ENV PORT=8080
EXPOSE 8080

# Aplica migraciones y levanta el servidor. alembic upgrade head es idempotente:
# no hace nada si la base ya está al día.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
