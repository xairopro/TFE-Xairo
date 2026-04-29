#!/bin/bash
# =============================================================
# Monterrei Core - arranque
# - Activa o venv en ~/Documents/Monterrei_Venv
# - Crea o venv se non existe e instala dependencias
# - Lanza Uvicorn co módulo app.main:asgi
# =============================================================

set -e

VENV_DIR="$HOME/Documents/Monterrei_Venv"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="/tmp/monterrei_core.pid"

cd "$SCRIPT_DIR"

if [ ! -d "$VENV_DIR" ]; then
    echo "[Monterrei] Creando venv en $VENV_DIR ..."
    /usr/bin/env python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

source "$VENV_DIR/bin/activate"

# Instala dependencias se faltan (idempotente, rápido se xa están)
pip install -q -r "$SCRIPT_DIR/requirements.txt" >/dev/null 2>&1 || true

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[Monterrei] Xa hai unha instancia activa (PID $OLD_PID). Detén con stop.command"
        exit 1
    fi
fi

echo "[Monterrei] Lanzando servidor..."
echo "[Monterrei] Músicos / Director         -> http://<ip>:8000"
echo "[Monterrei] Admin + Proxección (con contrasinal) -> http://<ip>:8800"
echo "[Monterrei] Público                    -> http://<ip>:8001 (e :80 se está activo)"

# --- Auto-abrir Admin + Proxección en Chrome --------------------------------
# Le credenciais e portos do .env
ADMIN_USER=$(grep -E "^MONTERREI_ADMIN_USER" "$SCRIPT_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2 | tr -d ' "')
ADMIN_PASS=$(grep -E "^MONTERREI_ADMIN_PASSWORD" "$SCRIPT_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2 | tr -d ' "')
PORT_ADMIN=$(grep -E "^MONTERREI_PORT_ADMIN" "$SCRIPT_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2 | tr -d ' "')
ADMIN_USER=${ADMIN_USER:-xairo}
ADMIN_PASS=${ADMIN_PASS:-xairocampos}
PORT_ADMIN=${PORT_ADMIN:-8800}
ADMIN_URL="http://${ADMIN_USER}:${ADMIN_PASS}@127.0.0.1:${PORT_ADMIN}/admin"
PROJ_URL="http://${ADMIN_USER}:${ADMIN_PASS}@127.0.0.1:${PORT_ADMIN}/projection"
HEALTH_URL="http://127.0.0.1:${PORT_ADMIN}/api/health"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Subshell que agarda a que o servidor responda e abre dúas ventás de Chrome.
# Faise en segundo plano para non bloquear o arranque do servidor.
# Se imos elevar con sudo, este subshell mantense co usuario actual ($USER).
( for i in $(seq 1 60); do
    if curl -sf -o /dev/null --max-time 1 "$HEALTH_URL"; then
      break
    fi
    sleep 0.5
  done
  if [ -x "$CHROME" ]; then
    echo "[Monterrei] Abrindo Chrome (admin + proxección)..."
    # Admin: ventá normal
    "$CHROME" --new-window "$ADMIN_URL" >/dev/null 2>&1 &
    sleep 0.6
    # Proxección: ventá modo app (sen barra de marcadores nin pestañas)
    "$CHROME" --new-window --app="$PROJ_URL" >/dev/null 2>&1 &
  else
    echo "[Monterrei] Google Chrome non instalado en /Applications. Abrindo no navegador por defecto..."
    open "$ADMIN_URL"
    sleep 0.6
    open "$PROJ_URL"
  fi
) &

# Se BIND_PORT_80=true e non somos root, re-executamos con sudo
BIND80=$(grep -E "^MONTERREI_BIND_PORT_80" "$SCRIPT_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2 | tr -d ' "')
if [ "$BIND80" = "true" ] && [ "$EUID" -ne 0 ]; then
    echo "[Monterrei] Porto 80 activo: precísase contrasinal de administrador..."
    exec sudo -E env "PATH=$PATH" "$VENV_DIR/bin/python" -m app.main
fi

# Lanzamento. main.py orquestra os tres portos internamente
python -m app.main &
APP_PID=$!
echo $APP_PID > "$PID_FILE"

echo "[Monterrei] PID=$APP_PID"
wait $APP_PID
