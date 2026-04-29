#!/bin/bash
# =============================================================
# Simulador de teléfonos para Monterrei Core
# - Activa o venv en ~/Documents/Monterrei_Venv
# - Instala aiohttp + python-socketio se faltan
# - Pregunta cantos músicos e cantos espectadores simular
# - Lanza simulate_70.py en modo verboso (mostra eventos do servidor)
# =============================================================
set -e

VENV_DIR="$HOME/Documents/Monterrei_Venv"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$SCRIPT_DIR"

if [ ! -d "$VENV_DIR" ]; then
    echo "[Stress] Creando venv en $VENV_DIR ..."
    /usr/bin/env python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
fi

source "$VENV_DIR/bin/activate"

echo "[Stress] Comprobando dependencias..."
pip install -q -r "$SCRIPT_DIR/requirements.txt" >/dev/null 2>&1 || true

DEFAULT_HOST="127.0.0.1"
DEFAULT_MUS=70
DEFAULT_PUB=30
DEFAULT_LIFE=180

echo ""
echo "==============================================="
echo "  Monterrei Stress Test (simulación local)     "
echo "==============================================="
echo ""
read -r -p "Host do servidor [$DEFAULT_HOST]: " HOST
HOST=${HOST:-$DEFAULT_HOST}
read -r -p "Cantos MÚSICOS simular? [$DEFAULT_MUS]: " MUS
MUS=${MUS:-$DEFAULT_MUS}
read -r -p "Cantos ESPECTADORES (público)? [$DEFAULT_PUB]: " PUB
PUB=${PUB:-$DEFAULT_PUB}
read -r -p "Segundos de vida por conexión [$DEFAULT_LIFE]: " LIFE
LIFE=${LIFE:-$DEFAULT_LIFE}

echo ""
echo "[Stress] Lanzando: $MUS músicos + $PUB público en $HOST (vida=${LIFE}s)"
echo "[Stress] Modo verboso activado: verás cada evento que recibe cada teléfono"
echo "[Stress] Premer Ctrl-C para parar"
echo ""

python "$SCRIPT_DIR/simulate_70.py" \
    --host "$HOST" \
    --musicians "$MUS" \
    --public "$PUB" \
    --lifetime "$LIFE" \
    --verbose
