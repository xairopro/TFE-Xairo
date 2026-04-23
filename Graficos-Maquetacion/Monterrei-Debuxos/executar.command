#!/bin/zsh
# run_castelo.command
# Double-click this file in Finder to run the SVG generator.

# Change to the folder where this script lives (so relative paths work)
cd "$(dirname "$0")"

ENV_PATH="$HOME/Documents/entornos_virtuais/castelo_env"

# ── Create the virtual environment if it doesn't exist yet ──
if [ ! -d "$ENV_PATH" ]; then
  echo "Creating virtual environment at $ENV_PATH …"
  python3 -m venv "$ENV_PATH"
fi

# ── Activate ──
source "$ENV_PATH/bin/activate"

# ── Install / upgrade dependencies silently if needed ──
pip install --quiet --upgrade opencv-python numpy cairosvg

# ── Run for Castelo ──
echo ""
echo "=== CASTELO DE MONTERREI ==="
echo "─────────────────────────────────────────"
python castelo_monterrei.py Castelo/castillo-de-monterrei.png Castelo castelo_monterrei

echo ""
echo "=== FORTE DA ATALAIA ==="
echo "─────────────────────────────────────────"
python castelo_monterrei.py "Forte/Forta-da-Atalaia_6-1024x682.jpg.webp" Forte forte_atalaia --no-video

echo ""
echo "─────────────────────────────────────────"
echo "Done. Outputs in Castelo/ and Forte/"
echo "Abrindo SVG animado do Castelo no navegador …"
open Castelo/castelo_monterrei_1.svg

# Keep the Terminal window open so you can read the output
echo ""
read -r "?Press Enter to close this window …"
