"""Movemento 1: vídeo do castelo de Monterrei.

A partir desta versión, M1 contén SÓ o vídeo. As imaxes previas pasaron a
unha sección independente (`previa.py`) accesible desde o admin.
"""
from __future__ import annotations

from ..config import settings
from ..core.broadcaster import to_projection


async def play_video():
    rel = "/static/assets/videos/" + settings.m1_video
    await to_projection("m1:video", {"action": "play", "src": rel})


async def stop_video():
    await to_projection("m1:video", {"action": "stop"})


async def clear_projection():
    await to_projection("m1:video", {"action": "stop"})
    # Tamén oculta calquera imaxe/QR previo activo (limpeza de pantalla total)
    from . import previa as _previa
    await _previa.clear_all()
