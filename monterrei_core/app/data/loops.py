"""Loops do Movemento 4 (foliada libre)."""
from __future__ import annotations

LOOPS: dict[str, list[str]] = {
    "L1":  ["saxalt1", "saxalt2", "saxten1", "saxten2", "saxbar", "piano", "arpa", "perc5", "electronica"],
    "L2":  ["clb", "saxten1", "saxten2", "saxbar", "trp1", "trp2", "trp3"],
    "L3":  ["trp1", "trp2", "trp3", "tpa1", "tpa2", "tpa3", "tpa4", "trb1", "trb2", "trb3", "trb4",
            "bomb", "tuba", "perc2", "perc4", "perc5", "perc6"],
    "L4":  ["fr1", "fr2", "vc", "cb", "perc1", "perc3"],
    "L5":  ["fr1", "fr2", "ob1", "ob2", "fg", "clreq", "cl1", "cl2", "cl3", "clb",
            "saxalt1", "saxalt2", "saxten1", "saxten2", "saxbar", "vc", "cb", "perc5"],
    "L6":  ["picc", "fr1", "fr2", "ob1", "ob2", "clreq", "cl1", "cl2", "cl3"],
    "L7":  ["saxten1", "saxten2", "trp1", "trp2", "trp3", "perc6"],
    "L8":  ["tpa1", "tpa2", "tpa3", "tpa4", "trb1", "trb2", "trb3", "trb4", "bomb", "tuba", "vc", "cb"],
    "L9":  ["picc", "trb1", "trb2", "trb3", "trb4", "bomb", "tuba", "vc", "cb", "perc4", "perc6"],
    "L10": ["fg", "cl1", "cl2", "cl3", "clb", "saxalt1", "saxalt2", "saxbar", "perc4", "perc6"],
}


# Cores neón por loop (HEX).
LOOP_COLORS: dict[str, str] = {
    "L1": "#00ffd9",
    "L2": "#ff00aa",
    "L3": "#a8ff00",
    "L4": "#ffaa00",
    "L5": "#bd00ff",
    "L6": "#ff5577",
    "L7": "#33ffe7",
    "L8": "#3377ff",
    "L9": "#ff7733",
    "L10": "#77ffaa",
}


def shared_instruments(loop_a: str, loop_b: str) -> set[str]:
    return set(LOOPS.get(loop_a, [])) & set(LOOPS.get(loop_b, []))
