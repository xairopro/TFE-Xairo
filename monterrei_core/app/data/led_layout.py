"""Mapeado físico dos 60 LEDs RGBW arredor do público.

Anel continuo: LED 1 = adiante-esquerda, percorre por detrás do público,
remata en adiante-dereita.

Para o Mov. 2: cada LED corresponde a un ángulo. As posicións dos
músicos en `topography.POSITIONS` proxéctanse a un ángulo (en graos)
desde o centro da escena, e ese ángulo mapea ao LED máis próximo.
"""
from __future__ import annotations
import math

from .topography import POSITIONS

# 60 LEDs distribuídos uniformemente no anel.
# Asumimos que o LED 0 está a un ángulo "frente-esquerda" (-150º desde +x)
# e crecen no sentido das agullas do reloxo polo redor do público.
LED_COUNT = 60


def led_angles_deg() -> list[float]:
    """Ángulo de cada LED en graos no rango [-180, 180]."""
    # Adiante-esq: ~ +135º, adiante-der: ~ +45º, atrás: ~ -90º
    # Percorrido continuo polo "lado lonxe" (atrás do público).
    out = []
    for i in range(LED_COUNT):
        t = i / (LED_COUNT - 1)  # 0..1
        # de 135º (esq) cara -45º (atrás-leste-x) ata 45º (der) pasando por 270 / -90
        # Calculemos así: ángulo = 135 - 360*t  (vai por -180/180, completando o anel).
        a = 135 - 360 * t
        # Normaliza a [-180,180]
        while a > 180: a -= 360
        while a <= -180: a += 360
        out.append(a)
    return out


LED_ANGLES = led_angles_deg()


def angle_of_instrument(base_id: str) -> float | None:
    pos = POSITIONS.get(base_id)
    if not pos:
        return None
    x, y = pos
    # Centro do círculo do público está detrás da banda: (0, 0.3)
    # Punto de orixe: o "público" no centro do salón
    cx, cy = 0.0, 0.3
    return math.degrees(math.atan2(y - cy, x - cx))


def led_for_instrument(base_id: str) -> int | None:
    a = angle_of_instrument(base_id)
    if a is None:
        return None
    # Atopa o LED cuxo ángulo está máis próximo
    best, best_d = None, float("inf")
    for i, la in enumerate(LED_ANGLES):
        d = abs(((a - la + 540) % 360) - 180)
        if d < best_d:
            best, best_d = i, d
    return best


# Sección DMX por loop (M4): rexión angular do anel.
# Cada loop ocupa unha franxa de 36º (10 loops -> volta completa).
def section_for_loop(loop_index_1based: int) -> list[int]:
    span = LED_COUNT // 10
    start = (loop_index_1based - 1) * span
    return list(range(start, start + span))
