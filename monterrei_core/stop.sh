#!/usr/bin/env bash
# Detén Monterrei Core de forma limpa.
PID_FILE="/tmp/monterrei_core.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "[Monterrei] PID file non atopado. Buscando proceso..."
    PIDS=$(pgrep -f "python.*-m app.main" || true)
    if [ -z "$PIDS" ]; then
        echo "[Monterrei] Nada que parar."
        exit 0
    fi
    for PID in $PIDS; do
        echo "[Monterrei] SIGTERM a PID $PID"
        kill -TERM "$PID" 2>/dev/null || true
    done
    sleep 2
    for PID in $PIDS; do
        kill -0 "$PID" 2>/dev/null && kill -KILL "$PID" 2>/dev/null || true
    done
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    echo "[Monterrei] Enviando SIGTERM a PID $PID..."
    kill -TERM "$PID"
    for _ in $(seq 1 10); do
        kill -0 "$PID" 2>/dev/null || break
        sleep 0.3
    done
    if kill -0 "$PID" 2>/dev/null; then
        echo "[Monterrei] Aínda activo, SIGKILL..."
        kill -KILL "$PID"
    fi
    echo "[Monterrei] Detido."
else
    echo "[Monterrei] PID $PID xa non está activo."
fi
rm -f "$PID_FILE"
