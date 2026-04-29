"""Mapeo do compás real (lineal) ao compás de partitura considerando
repeticións e casas de 1ª/2ª en 6/8.

Regras (vistas pola pista):
- Hai 8 compases de claqueta antes de "compás 1" da partitura.
- Pase 1: 1, 2..9, repetir (2..8), 10..18, rep (11..17), 19..27, rep (20..26),
  28..44.
- Pase 2+: 2..8, 10..17, 19..26, 28..44 (saltando casas de 1ª).
- Tras 44 vólvese a 2 cambiando de pase.

Esta función traduce un nº de compás "linear-tocado" (1, 2, 3...) ao
nº de compás visible para o músico/director, e marca o pase actual.
"""
from __future__ import annotations
from typing import NamedTuple


# Definición de cada pase como secuencia ordenada de compases visibles.
# Pase 1 (con repeticións): inclúe primeiro 1..9, despois loop 2..8, despois 10..18 etc.
PASE1: list[int] = (
    [1] + list(range(2, 10))           # 1, 2..9
    + list(range(2, 9))                # 2..8 (repetición, sin 9)
    + list(range(10, 19))              # 10..18
    + list(range(11, 18))              # 11..17 (rep)
    + list(range(19, 28))              # 19..27
    + list(range(20, 27))              # 20..26 (rep)
    + list(range(28, 45))              # 28..44
)

# Pase 2+ : saltando primeira casa.
PASE2: list[int] = (
    list(range(2, 9))                  # 2..8 (sálta 9)
    + list(range(10, 18))              # 10..17 (sálta 18)
    + list(range(19, 27))              # 19..26 (sálta 27)
    + list(range(28, 45))              # 28..44
)


class BarPos(NamedTuple):
    pass_number: int   # 1, 2, 3...  (0 = click-in)
    display_bar: int   # nº visible
    in_clickin: bool   # True se aínda estamos nos 8 compases de claqueta


def real_bar_to_display(real_bar_1based: int) -> BarPos:
    """real_bar_1based: 1 corresponde ao primeiro compás de claqueta tras START.

    Click-in ocupa real_bar 1..8.
    Música real comeza en real_bar 9 -> primeiro elemento de PASE1.
    """
    if real_bar_1based <= 0:
        return BarPos(0, 0, True)
    if real_bar_1based <= 8:
        return BarPos(0, real_bar_1based, True)

    music_index = real_bar_1based - 9  # 0-based índice na partitura
    # Pase 1
    if music_index < len(PASE1):
        return BarPos(1, PASE1[music_index], False)
    # Pases 2+
    music_index -= len(PASE1)
    pase = 2 + (music_index // len(PASE2))
    pos_in_pase = music_index % len(PASE2)
    return BarPos(pase, PASE2[pos_in_pase], False)


def real_bar_from_pulses(total_pulses: int, pulses_per_bar: int = 72) -> int:
    """Pulsos MIDI -> nº de compás real (1-based) dende o START."""
    if total_pulses <= 0:
        return 0
    return (total_pulses // pulses_per_bar) + 1


def beat_in_bar(total_pulses: int, pulses_per_bar: int = 72) -> int:
    """Devolve T (1 ou 2) en pulso composto (negra puntillada)."""
    pulses_in_bar = total_pulses % pulses_per_bar
    # 6/8 ten 2 negras puntilladas por compás. cada negra puntillada = 36 ticks.
    return (pulses_in_bar // 36) + 1
