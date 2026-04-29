#!/bin/bash
# =============================================================
# Configura redirección 80 -> 8001 con pfctl en macOS.
# Require sudo. Persiste ata o seguinte reinicio do equipo.
# =============================================================

set -e

RULE='rdr pass on lo0 inet proto tcp from any to any port 80 -> 127.0.0.1 port 8001
rdr pass on en0 inet proto tcp from any to any port 80 -> 127.0.0.1 port 8001
rdr pass on en1 inet proto tcp from any to any port 80 -> 127.0.0.1 port 8001'

TMP=/tmp/monterrei_pf.conf
echo "$RULE" > "$TMP"

echo "[Monterrei] Cargando regras pfctl (require sudo)..."
sudo pfctl -ef "$TMP" || true
echo "[Monterrei] Listo. O porto 80 redirixe a 8001."
echo "[Monterrei] Para revertir: sudo pfctl -d"
