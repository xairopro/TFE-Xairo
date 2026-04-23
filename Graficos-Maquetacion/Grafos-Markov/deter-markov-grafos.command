#!/bin/bash
# ── Deter o servidor Flask de Markov Grafos ──

PORT=5050

# Buscar PID do proceso na porta 5050
PID=$(lsof -ti tcp:$PORT 2>/dev/null)

if [ -n "$PID" ]; then
    kill "$PID" 2>/dev/null
    echo "✓ Servidor detido (PID $PID, porto $PORT)."
else
    echo "⚠ Non se atopou ningún proceso na porta $PORT."
fi

echo ""
echo "Preme calquera tecla para pechar esta ventá..."
read -n 1
