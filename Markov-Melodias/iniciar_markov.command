#!/bin/zsh

# Pechar o proceso que estea a usar o porto 5000, se o hai
lsof -ti:5000 | xargs kill -9 2>/dev/null

# Ir ao directorio do proxecto
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Executar o servidor Flask usando o contorno virtual externo do usuario
EXTERNAL_VENV="$HOME/Documents/entornos virtuales/venv-markov-melodias"

if [ -x "$EXTERNAL_VENV/bin/python" ]; then
    "$EXTERNAL_VENV/bin/python" markov_web.py
else
    python3 markov_web.py
fi
