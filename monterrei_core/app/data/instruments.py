"""Catálogo de instrumentos. Cada un cunha id curta, nome humano e
contador de duplicados manexado polo session_manager.

Convención de id: minúsculas, sen espazos. Os duplicados engaden "-N".
Director vai como un máis no dropdown.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Instrument:
    id: str
    label: str
    section: str = ""   # vento-madeira | vento-metal | percusión | corda | dirección | electrónica


CATALOG: list[Instrument] = [
    # Madeira
    Instrument("picc", "Piccolo", "vento-madeira"),
    Instrument("fr1", "Frauta 1", "vento-madeira"),
    Instrument("fr2", "Frauta 2", "vento-madeira"),
    Instrument("fralto", "Frauta Alto", "vento-madeira"),
    Instrument("ob1", "Óboe 1", "vento-madeira"),
    Instrument("ob2", "Óboe 2", "vento-madeira"),
    Instrument("fg", "Fagot", "vento-madeira"),
    Instrument("clreq", "Clarinete Requinto", "vento-madeira"),
    Instrument("cl1", "Clarinete 1", "vento-madeira"),
    Instrument("cl2", "Clarinete 2", "vento-madeira"),
    Instrument("cl3", "Clarinete 3", "vento-madeira"),
    Instrument("clb", "Clarinete Baixo", "vento-madeira"),
    Instrument("saxsop", "Saxofón Soprano", "vento-madeira"),
    Instrument("saxalt1", "Saxofón Alto 1", "vento-madeira"),
    Instrument("saxalt2", "Saxofón Alto 2", "vento-madeira"),
    Instrument("saxten1", "Saxofón Tenor 1", "vento-madeira"),
    Instrument("saxten2", "Saxofón Tenor 2", "vento-madeira"),
    Instrument("saxbar", "Saxofón Barítono", "vento-madeira"),
    # Metal
    Instrument("trp1", "Trompeta 1", "vento-metal"),
    Instrument("trp2", "Trompeta 2", "vento-metal"),
    Instrument("trp3", "Trompeta 3", "vento-metal"),
    Instrument("tpa1", "Trompa 1", "vento-metal"),
    Instrument("tpa2", "Trompa 2", "vento-metal"),
    Instrument("tpa3", "Trompa 3", "vento-metal"),
    Instrument("tpa4", "Trompa 4", "vento-metal"),
    Instrument("trb1", "Trombón 1", "vento-metal"),
    Instrument("trb2", "Trombón 2", "vento-metal"),
    Instrument("trb3", "Trombón 3", "vento-metal"),
    Instrument("trb4", "Trombón 4", "vento-metal"),
    Instrument("bomb", "Bombardino", "vento-metal"),
    Instrument("tuba", "Tuba", "vento-metal"),
    # Corda
    Instrument("vc", "Violonchelo", "corda"),
    Instrument("cb", "Contrabaixo", "corda"),
    Instrument("arpa", "Arpa", "corda"),
    Instrument("piano", "Piano", "corda"),
    # Percusión
    Instrument("perc1", "Percusión 1", "percusión"),
    Instrument("perc2", "Percusión 2", "percusión"),
    Instrument("perc3", "Percusión 3", "percusión"),
    Instrument("perc4", "Percusión 4", "percusión"),
    Instrument("perc5", "Percusión 5", "percusión"),
    Instrument("perc6", "Percusión 6", "percusión"),
    # Outros
    Instrument("electronica", "Electrónica", "electrónica"),
    # Dirección
    Instrument("director", "Director", "dirección"),
]


CATALOG_BY_ID: dict[str, Instrument] = {i.id: i for i in CATALOG}


def assign_unique_id(base_id: str, existing_ids: set[str]) -> tuple[str, str]:
    """Devolve (id_único, label_humano) para múltiples ocupantes do mesmo posto.

    Se base_id non está usado -> devólvese tal cal.
    Se está usado -> engade "-N" (e ao primeiro renómealle a "-1").
    """
    base = CATALOG_BY_ID.get(base_id)
    if base is None:
        raise ValueError(f"Instrumento descoñecido: {base_id}")

    same_base = [eid for eid in existing_ids if eid == base_id or eid.startswith(base_id + "-")]
    if not same_base:
        return base_id, base.label
    # Hai outros. Atopa o seguinte índice libre.
    used_indices = set()
    for eid in same_base:
        if eid == base_id:
            used_indices.add(1)
        else:
            try:
                used_indices.add(int(eid.split("-")[-1]))
            except ValueError:
                pass
    n = 1
    while n in used_indices:
        n += 1
    new_id = f"{base_id}-{n}"
    new_label = f"{base.label} - {n}"
    return new_id, new_label


def base_id_of(instrument_id: str) -> str:
    """Quita o sufixo -N. 'cl3-2' -> 'cl3'."""
    if "-" in instrument_id and instrument_id.rsplit("-", 1)[1].isdigit():
        return instrument_id.rsplit("-", 1)[0]
    return instrument_id
