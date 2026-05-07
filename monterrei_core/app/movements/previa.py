"""Sección 'Previo' (independente de M1):
- Slideshow de fotos en `static/assets/m1_previas/`.
- Pantalla con QR + texto WiFi + xairo.gal.

M1 queda só co vídeo do castelo de Monterrei.
"""
from __future__ import annotations
import io
import os
from pathlib import Path
from typing import Optional

from ..config import settings, BASE_DIR
from ..core.broadcaster import to_projection


# ---------------------------------------------------------------- Previas ---

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
    await to_projection("previa:slideshow", {"index": index, "src": imgs[index], "total": len(imgs)})


async def hide_image():
    await to_projection("previa:slideshow", {"index": -1, "src": None, "total": 0})


# -------------------------------------------------------------------- QR ---

def _make_qr_svg(text: str) -> str:
    """Xera un QR como SVG en string (sen dependencia de PIL)."""
    import qrcode  # type: ignore
    import qrcode.image.svg  # type: ignore
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(text, image_factory=factory, box_size=12, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


async def show_qr(url: Optional[str] = None,
                  wifi_ssid: str = "Monterrei",
                  wifi_pass: str = "foliada7",
                  footer: str = "xairo.gal"):
    target = url or f"http://{settings.prod_ip}/"
    try:
        svg = _make_qr_svg(target)
    except Exception as e:  # noqa
        # Fallback: payload sen SVG; o cliente debuxará só o texto.
        svg = ""
    await to_projection("previa:qr_show", {
        "url": target,
        "svg": svg,
        "wifi_ssid": wifi_ssid,
        "wifi_pass": wifi_pass,
        "footer": footer,
    })


async def hide_qr():
    await to_projection("previa:qr_hide", {})


async def clear_all():
    """Quita calquera contido da sección Previo na proxección."""
    await hide_image()
    await hide_qr()
