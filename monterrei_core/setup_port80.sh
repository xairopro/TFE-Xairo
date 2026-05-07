#!/usr/bin/env bash
# =============================================================
# Redirección 80 -> 8001 con iptables (Ubuntu/Linux).
# Require sudo. As regras non persisten tras reinicio salvo que se
# instale iptables-persistent. Para revertir: sudo ./setup_port80.sh --off
# =============================================================
set -e

PORT_DST="${MONTERREI_PORT_PUBLIC:-8001}"

if [ "$EUID" -ne 0 ]; then
    echo "[Monterrei] Re-executando con sudo..."
    exec sudo -E "$0" "$@"
fi

if [ "$1" = "--off" ] || [ "$1" = "off" ]; then
    echo "[Monterrei] Eliminando regras de redirección 80 -> ${PORT_DST}..."
    iptables -t nat -D PREROUTING -p tcp --dport 80 -j REDIRECT --to-port "$PORT_DST" 2>/dev/null || true
    iptables -t nat -D OUTPUT     -p tcp -o lo --dport 80 -j REDIRECT --to-port "$PORT_DST" 2>/dev/null || true
    echo "[Monterrei] Regras eliminadas (se existían)."
    exit 0
fi

echo "[Monterrei] Engadindo redirección 80 -> ${PORT_DST} (iptables nat)..."
# Tráfico entrante desde a rede
iptables -t nat -C PREROUTING -p tcp --dport 80 -j REDIRECT --to-port "$PORT_DST" 2>/dev/null \
    || iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port "$PORT_DST"
# Tráfico local (loopback)
iptables -t nat -C OUTPUT -p tcp -o lo --dport 80 -j REDIRECT --to-port "$PORT_DST" 2>/dev/null \
    || iptables -t nat -A OUTPUT     -p tcp -o lo --dport 80 -j REDIRECT --to-port "$PORT_DST"

echo "[Monterrei] Listo. O porto 80 redirixe a ${PORT_DST}."
echo "[Monterrei] Para revertir: sudo $0 --off"
