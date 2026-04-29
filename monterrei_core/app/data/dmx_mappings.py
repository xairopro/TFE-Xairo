"""Mapeado de cores DMX por movemento, grupo e loop."""
from .groups import GROUP_RGBW
from .loops import LOOP_COLORS

# RGBW por defecto en repouso
IDLE_RGBW = (0, 0, 0, 0)


def hex_to_rgbw(h: str) -> tuple[int, int, int, int]:
    h = h.lstrip("#")
    if len(h) == 6:
        r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
        return (r, g, b, 0)
    raise ValueError(h)


LOOP_RGBW = {k: hex_to_rgbw(v) for k, v in LOOP_COLORS.items()}
