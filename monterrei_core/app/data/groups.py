"""Grupos de Lorenz (Movemento 2). Refírense a base_instrument_id (sen sufixo)."""

GROUPS: dict[str, list[str]] = {
    "G1": [
        "picc", "fr1", "clreq", "cl1", "clb", "saxbar",
        "trb3", "trb4", "bomb", "tuba", "piano", "cb",
        "perc3", "perc5", "perc6",
    ],
    "G2": [
        "fr2", "fralto", "ob1", "ob2", "fg", "cl2", "cl3",
        "saxalt1", "saxalt2", "saxten1", "saxten2",
        "trb1", "trb2", "vc", "arpa", "perc1", "perc2",
    ],
    "G3": [
        "saxsop", "tpa1", "tpa2", "tpa3", "tpa4",
        "trp1", "trp2", "trp3", "perc4",
    ],
}

# Cores asociadas (RGB neón). G1 = verde monte, G2 = ámbar, G3 = vermello caos.
GROUP_COLOR_HEX: dict[str, str] = {
    "G1": "#1eff7e",
    "G2": "#ffae0a",
    "G3": "#ff2a55",
}

# Cores RGBW (0-255) para DMX.
GROUP_RGBW: dict[str, tuple[int, int, int, int]] = {
    "G1": (30, 255, 126, 0),
    "G2": (255, 174, 10, 0),
    "G3": (255, 42, 85, 0),
}


def all_instruments_of_groups(groups: list[str]) -> set[str]:
    out: set[str] = set()
    for g in groups:
        out.update(GROUPS.get(g, []))
    return out
