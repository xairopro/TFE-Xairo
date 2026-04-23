#!/usr/bin/env zsh
cd "$(dirname "$0")"

ENV_DIR="$HOME/Documents/entornos_virtuais/castelo_env"

if [[ ! -d "$ENV_DIR" ]]; then
    echo "ERROR: Virtual environment not found at $ENV_DIR"
    echo "Run executar.command first to create it."
    read -r _
    exit 1
fi

source "$ENV_DIR/bin/activate"

SVG_FILE="Castelo/castelo_monterrei_1.svg"

if [[ ! -f "$SVG_FILE" ]]; then
    echo "ERROR: $SVG_FILE not found."
    echo "Run executar.command first to generate the SVGs."
    read -r _
    exit 1
fi

echo "=== Exporting Castelo video ==="
python castelo_monterrei.py Castelo/castillo-de-monterrei.png Castelo castelo_monterrei

echo ""
echo "Preme calquera tecla para pechar…"
read -r _
