"""Topografía da banda: 4 semicírculos S1..S4 (interior -> exterior, esquerda -> dereita).

Coordenadas normalizadas (x in [-1,1], y in [0,1]) sobre un mapa 2D.
Y crece cara atrás (lonxe do público).

Esta capa sérvelle a Lorenz para mapear a traxectoria 2D a "celas" de músicos.
"""
from __future__ import annotations
import math


# Orde dos instrumentos por semicírculo (esquerda -> dereita).
SEMICIRCLES: dict[str, list[str]] = {
    "S1": ["fralto", "fr1", "fr2", "picc", "ob2", "ob1"],
    "S2": ["cl1", "clb", "tpa4", "tpa3", "tpa2", "tpa1", "bomb", "saxalt1", "saxalt2", "saxsop"],
    "S3": ["cl2", "arpa", "trp3", "trp2", "trp1", "trb1", "trb2", "trb3", "trb4", "saxbar", "saxten1", "saxten2"],
    "S4": ["cl3", "piano", "perc1", "perc2", "perc3", "perc4", "perc5", "perc6", "tuba", "cb", "vc"],
}

# Radio de cada semicírculo (normalizado).
SEMI_RADIUS = {"S1": 0.25, "S2": 0.45, "S3": 0.7, "S4": 0.95}


def positions_2d() -> dict[str, tuple[float, float]]:
    """Devolve {base_instrument_id: (x, y)} repartido equiespaciado en cada arco."""
    out: dict[str, tuple[float, float]] = {}
    for sem, instruments in SEMICIRCLES.items():
        r = SEMI_RADIUS[sem]
        n = len(instruments)
        # ángulos de pi (esquerda) a 0 (dereita), pasando por pi/2 (centro).
        for i, inst in enumerate(instruments):
            t = (i + 0.5) / n
            angle = math.pi * (1 - t)  # esq=pi -> der=0
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            out[inst] = (round(x, 4), round(y, 4))
    return out


POSITIONS = positions_2d()


def closest_instrument(x: float, y: float, only_in: set[str] | None = None,
                       exclude: set[str] | None = None) -> str | None:
    """Devolve o base_instrument_id da cela máis próxima ao punto (x,y)."""
    best, best_d = None, float("inf")
    for inst, (ix, iy) in POSITIONS.items():
        if only_in is not None and inst not in only_in:
            continue
        if exclude is not None and inst in exclude:
            continue
        d = (x - ix) ** 2 + (y - iy) ** 2
        if d < best_d:
            best, best_d = inst, d
    return best
