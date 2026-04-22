#!/usr/bin/env python3
"""Proba rápida de _split_into_measures."""
import sys
sys.path.insert(0, ".")
from app import _split_into_measures

def show(label, beats):
    print(f"\n--- {label} ---")
    print(f"  beats = {beats}")
    measures = _split_into_measures(beats, 36)
    for i, m in enumerate(measures):
        total = sum(e["ticks"] for e in m)
        desc = []
        for e in m:
            ts = "T>" if e["tie_start"] else "  "
            tp = "<T" if e["tie_stop"]  else "  "
            desc.append(f"{tp}{e['ticks']:2d}{ts}")
        print(f"  Compás {i+1}: {total:3d} ticks | {' '.join(desc)}")

    # Caso 1: desborda a lóxica anterior (12+6+6+6+6+6+4 = 46 > 36)
    show("Desbordamento do código anterior", [1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.333])

    # Caso 2: exactamente 2 compases (18+18+24+12 = 72)
    show("Negra con punto e branca cruzando", [1.5, 1.5, 2.0, 1.0])

    # Caso 3: 4 negras (48 ticks, a nota cruza a barra)
    show("4 negras cruzando a barra", [1.0, 1.0, 1.0, 1.0])

    # Caso 4: redonda (48 ticks, maior ca un compás)
    show("Redonda", [4.0, 0.5])

    # Caso 5: 6 corcheas = exactamente un compás
    show("6 corcheas exactas", [0.5, 0.5, 0.5, 0.5, 0.5, 0.5])

    # Caso 6: mestura con ligaduras esperadas
    show("Cruce mixto", [1.0, 1.0, 0.666, 0.5, 0.5, 0.5])
