@echo off
REM Arranque local del Sistema de Contratos y Licitaciones.
REM Usa uv (https://docs.astral.sh/uv/) si esta disponible; si no, un venv con Python 3.10+.
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if %errorlevel%==0 (
  set "PY=uv run --no-project --python 3.12 --with-requirements requirements.txt python"
) else (
  if not exist .venv (
    python -m venv .venv || (echo No se encontro Python ni uv. & pause & exit /b 1)
    .venv\Scripts\python -m pip install -r requirements.txt
  )
  set "PY=.venv\Scripts\python"
)

echo Preparando base de datos...
%PY% -m scripts.init_db

echo Abriendo el panel en el navegador...
start "" http://127.0.0.1:8000/panel

echo Iniciando servidor (Ctrl+C para detener)...
%PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8000

endlocal
