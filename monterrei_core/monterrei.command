#!/bin/bash
# Monterrei Core - Lanzador
#
# - Activa o venv en ~/Documents/Monterrei_Venv (créao se non existe).
# - Instala dependencias se faltan.
# - Lanza o servidor.
#
# Variables de entorno relevantes (poden definirse no .env):
#   MONTERREI_BIND_PORT_80=true   -> ademais de :8000/:8001 escoita en :80 (precisa sudo)
#
# Se BIND_PORT_80=true e non somos root, relanza con sudo.

set -e
cd "$(dirname "$0")"

VENV="$HOME/Documents/Monterrei_Venv"

# Crear venv se non existe
if [ ! -d "$VENV" ]; then
    echo ">> Creando venv en $VENV ..."
    python3 -m venv "$VENV"
fi

# Activar
source "$VENV/bin/activate"

# Instalar dependencias se hai requirements.txt máis novo que o sentinel
SENTINEL="$VENV/.monterrei_installed"
if [ ! -f "$SENTINEL" ] || [ requirements.txt -nt "$SENTINEL" ]; then
    echo ">> Instalando dependencias ..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    touch "$SENTINEL"
fi

# Lectura simple de MONTERREI_BIND_PORT_80 do .env
BIND80="false"
if [ -f .env ]; then
    BIND80=$(grep -E "^MONTERREI_BIND_PORT_80" .env | head -1 | cut -d= -f2 | tr -d ' "' || echo "false")
fi

if [ "$BIND80" = "true" ] || [ "$BIND80" = "True" ] || [ "$BIND80" = "1" ]; then
    if [ "$EUID" -ne 0 ]; then
        echo ">> MONTERREI_BIND_PORT_80=true e non son root. Relanzando con sudo ..."
        echo "   (Vaite pedir o contrasinal de administrador para abrir o porto 80)"
        exec sudo -E env "PATH=$PATH" "$VENV/bin/python" -m app.main
    fi
fi

# Lanzar normal
echo ">> Arrincando Monterrei Core ..."
echo "   Admin/Músico/Director/Proxección: http://localhost:8000"
echo "   Público:                          http://localhost:8001"
[ "$BIND80" = "true" ] && echo "   Público (porto 80):               http://localhost/"
echo ""
exec python -m app.main
