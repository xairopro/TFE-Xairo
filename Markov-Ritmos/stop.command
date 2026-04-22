#!/bin/zsh
echo "Detendo o servidor da muiñeira…"
lsof -ti:5000 | xargs kill -9 2>/dev/null && echo "Servidor detido." || echo "Non hai ningún servidor escoitando no porto 5000."
