#!/bin/zsh
# ── Grafo Futurista de Markov — Iniciador ──
# Fai dobre clic neste ficheiro dende o Finder para lanzar a app.

# Ir á carpeta do proxecto (onde está este ficheiro)
cd "$(dirname "$0")"

VENV="$HOME/Documents/venvs/venv-portada-grafos"
PORT=5050

# Crear o venv se non existe
if [ ! -d "$VENV" ]; then
    echo "🔧 Creando entorno virtual en $VENV ..."
    python3 -m venv "$VENV"
fi

# Activar o venv
source "$VENV/bin/activate"

# Instalar dependencias se faltan
pip install -q -r requirements.txt

# Matar calquera instancia previa na mesma porta
PID=$(lsof -ti :$PORT 2>/dev/null)
if [ -n "$PID" ]; then
    echo "⚠️  Parando servidor anterior (PID $PID) ..."
    kill "$PID" 2>/dev/null
    sleep 1
fi

# Abrir o navegador un segundo despois de que o servidor arranque
(sleep 1.5 && open "http://localhost:$PORT") &

echo "🚀 Iniciando Grafo Futurista de Markov en http://localhost:$PORT"
echo "   Preme Control+C para deter o servidor."
echo ""

# Iniciar o servidor Flask
python server.py
