#!/bin/bash
# Detén Monterrei Core de forma limpa.

PID_FILE="/tmp/monterrei_core.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "[Monterrei] PID file non atopado. Nada que parar."
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    echo "[Monterrei] Enviando SIGTERM a PID $PID..."
    kill -TERM "$PID"
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
        echo "[Monterrei] Aínda activo, SIGKILL..."
        kill -KILL "$PID"
    fi
    echo "[Monterrei] Detido."
else
    echo "[Monterrei] PID $PID xa non está activo."
fi
rm -f "$PID_FILE"
