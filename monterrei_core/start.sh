#!/usr/bin/env bash
# =============================================================
# Monterrei Core - arranque (Ubuntu/Linux)
# - Crea/usa o venv en ~/Documents/Monterrei_Venv
# - Instala dependencias se faltan
# - Lanza app.main (FastAPI + Socket.IO en varios portos)
# - Opcionalmente abre Admin + Proxección no navegador local
# =============================================================
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

DOCS_DIR="$HOME/Documents"
VENV_DIR="$DOCS_DIR/Monterrei_Venv"
PID_FILE="/tmp/monterrei_core.pid"

mkdir -p "$DOCS_DIR"

if [ ! -d "$VENV_DIR" ]; then
    echo "[Monterrei] Creando venv en $VENV_DIR ..."
    /usr/bin/env python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Instalar deps se requirements.txt é máis novo que sentinel
SENTINEL="$VENV_DIR/.monterrei_installed"
if [ ! -f "$SENTINEL" ] || [ "$SCRIPT_DIR/requirements.txt" -nt "$SENTINEL" ]; then
    echo "[Monterrei] Instalando dependencias ..."
    pip install -q --upgrade pip
    pip install -q -r "$SCRIPT_DIR/requirements.txt"
    touch "$SENTINEL"
fi

# Comprobar instancia previa
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[Monterrei] Xa hai unha instancia activa (PID $OLD_PID). Detén con ./stop.sh"
        exit 1
    fi
    rm -f "$PID_FILE"
fi

# Ler valores do .env
get_env() {
    local key="$1" default="$2"
    local val=""
    if [ -f "$SCRIPT_DIR/.env" ]; then
        val=$(grep -E "^${key}=" "$SCRIPT_DIR/.env" | head -1 | cut -d= -f2- | tr -d ' "')
    fi
    echo "${val:-$default}"
}

ADMIN_USER=$(get_env MONTERREI_ADMIN_USER xairo)
ADMIN_PASS=$(get_env MONTERREI_ADMIN_PASSWORD xairocampos)
PORT_ADMIN=$(get_env MONTERREI_PORT_ADMIN 8800)
PORT_MAIN=$(get_env MONTERREI_PORT_MAIN 8000)
PORT_PUBLIC=$(get_env MONTERREI_PORT_PUBLIC 8001)
BIND80=$(get_env MONTERREI_BIND_PORT_80 false)
AUTO_OPEN=$(get_env MONTERREI_AUTO_OPEN_BROWSER false)

echo "[Monterrei] Lanzando servidor..."
echo "[Monterrei] Músicos / Director       -> http://<ip>:${PORT_MAIN}"
echo "[Monterrei] Admin + Proxección       -> http://<ip>:${PORT_ADMIN}  (HTTP Basic)"
echo "[Monterrei] Público                  -> http://<ip>:${PORT_PUBLIC}"
[ "$BIND80" = "true" ] && echo "[Monterrei] Público (porto 80)       -> http://<ip>/"

# Auto-abrir navegador en local (opcional)
if [ "$AUTO_OPEN" = "true" ]; then
    BROWSER_BIN=""
    for b in google-chrome chromium chromium-browser firefox; do
        if command -v "$b" >/dev/null 2>&1; then
            BROWSER_BIN="$(command -v "$b")"; break
        fi
    done
    if [ -n "$BROWSER_BIN" ]; then
        ADMIN_URL="http://${ADMIN_USER}:${ADMIN_PASS}@127.0.0.1:${PORT_ADMIN}/admin"
        PROJ_URL="http://${ADMIN_USER}:${ADMIN_PASS}@127.0.0.1:${PORT_ADMIN}/projection"
        HEALTH_URL="http://127.0.0.1:${PORT_ADMIN}/api/health"
        ( for _ in $(seq 1 60); do
            if curl -sf -o /dev/null --max-time 1 "$HEALTH_URL"; then break; fi
            sleep 0.5
          done
          echo "[Monterrei] Abrindo navegador (admin + proxección)..."
          "$BROWSER_BIN" --new-window "$ADMIN_URL" >/dev/null 2>&1 &
          sleep 0.6
          if [[ "$BROWSER_BIN" == *chrome* || "$BROWSER_BIN" == *chromium* ]]; then
              "$BROWSER_BIN" --new-window --app="$PROJ_URL" >/dev/null 2>&1 &
          else
              "$BROWSER_BIN" --new-window "$PROJ_URL" >/dev/null 2>&1 &
          fi
        ) &
    else
        echo "[Monterrei] Aviso: ningún navegador atopado para auto-apertura."
    fi
fi

# Porto 80 require root
if [ "$BIND80" = "true" ] && [ "$EUID" -ne 0 ]; then
    echo "[Monterrei] Porto 80 activo: re-lanzando con sudo..."
    exec sudo -E env "PATH=$PATH" "$VENV_DIR/bin/python" -m app.main
fi

# Lanzamento
python -m app.main &
APP_PID=$!
echo "$APP_PID" > "$PID_FILE"
echo "[Monterrei] PID=$APP_PID"

trap 'echo "[Monterrei] Sinal recibido, parando..."; kill -TERM "$APP_PID" 2>/dev/null || true; wait "$APP_PID" 2>/dev/null || true; rm -f "$PID_FILE"; exit 0' INT TERM

wait "$APP_PID"
rm -f "$PID_FILE"
