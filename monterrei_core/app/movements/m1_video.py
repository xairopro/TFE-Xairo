"""Movemento 1: imaxes previas + MP4."""
from __future__ import annotations
import os
from pathlib import Path

from ..config import settings, BASE_DIR
from ..core.broadcaster import to_projection
from ..state import state


def list_previas() -> list[str]:
    """Devolve a lista ordenada de imaxes (rutas relativas a /static/) en m1_previas."""
    folder = settings.m1_previas_path
    folder.mkdir(parents=True, exist_ok=True)
    items = []
    for entry in sorted(os.scandir(folder), key=lambda e: e.name):
        if entry.is_file() and entry.name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            rel = Path("/").joinpath(Path(entry.path).relative_to(BASE_DIR)).as_posix()
            items.append(rel)
    return items


async def show_image(index: int):
    imgs = list_previas()
    if not imgs:
        return
    index = max(0, min(len(imgs) - 1, index))
    await to_projection("m1:slideshow", {"index": index, "src": imgs[index], "total": len(imgs)})


async def play_video():
    rel = "/static/assets/videos/" + settings.m1_video
    await to_projection("m1:video", {"action": "play", "src": rel})


async def stop_video():
    await to_projection("m1:video", {"action": "stop"})


async def clear_projection():
    await to_projection("m1:slideshow", {"index": -1, "src": None, "total": 0})
    await to_projection("m1:video", {"action": "stop"})
