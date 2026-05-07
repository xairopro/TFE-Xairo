#!/usr/bin/env bash
# Atallo: equivalente a ./start.sh
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
exec "$SCRIPT_DIR/start.sh" "$@"
