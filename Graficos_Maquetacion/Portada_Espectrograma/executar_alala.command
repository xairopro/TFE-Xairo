#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  executar_alala.command
#  Fai dobre clic neste ficheiro no Finder para xerar a portada.
# ─────────────────────────────────────────────────────────
set -euo pipefail

DIR_ENTORNO="$HOME/Documents/entornos_virtuais/alala_cover_env"
DIR_SCRIPT="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PYTHON="$DIR_SCRIPT/xerar_arte_alala.py"

echo "════════════════════════════════════════════"
echo "  Xerador de Portada — Alalá"
echo "════════════════════════════════════════════"

# ── 1. Crear o entorno virtual se non existe ───────────
if [ ! -d "$DIR_ENTORNO" ]; then
    echo "▸ Creando entorno virtual en $DIR_ENTORNO …"
    python3 -m venv "$DIR_ENTORNO"
fi

# ── 2. Activar ────────────────────────────────────────
echo "▸ Activando entorno virtual …"
source "$DIR_ENTORNO/bin/activate"

# ── 3. Instalar / actualizar dependencias ─────────────
echo "▸ Instalando dependencias …"
pip install --upgrade pip --quiet
pip install --upgrade librosa matplotlib numpy scipy --quiet

# ── 4. Executar o xerador ─────────────────────────────
echo "▸ Executando xerar_arte_alala.py …"
python "$SCRIPT_PYTHON"

echo ""
echo "════════════════════════════════════════════"
echo "  Rematado — mira portada_alala.png e portada_alala.svg"
echo "════════════════════════════════════════════"

# Manter a xanela do Terminal aberta
read -rp "Preme Intro para pechar…"
