#!/usr/bin/env python3
"""
Biblioteca principal do xerador rítmico con cadeas de Markov.

Le ficheiros MIDI, extrae as razóns dos intervalos entre ataques de cada pista,
constrúe unha cadea global de segunda orde e xera novas secuencias rítmicas.
"""

import glob
import os
import random
from collections import defaultdict

import pretty_midi

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
ONSET_THRESHOLD = 0.01  # segundos: ataques máis próximos fusiónanse
ALLOWED_RATIOS = [0.25, 0.333, 0.5, 0.666, 1.0, 1.5, 2.0, 3.0, 4.0]
RATIO_TOLERANCE = 0.05  # 5 %

RATIO_LABEL = {
    0.25: "1/4", 0.333: "1/3", 0.5: "1/2", 0.666: "2/3",
    1.0: "1", 1.5: "3/2", 2.0: "2", 3.0: "3", 4.0: "4",
}

# Nomes das figuras ↔ valores de razón (usado pola interface)
# A persoa usuaria escolle figuras; internamente trabállase con razóns.
NOTE_NAMES = [
    ("whole",           "Redonda (semibreve)",           4.0),
    ("dotted-half",     "Branca con punto",              3.0),
    ("half",            "Branca (mínima)",               2.0),
    ("dotted-quarter",  "Negra con punto",               1.5),
    ("quarter",         "Negra (semínima)",              1.0),
    ("dotted-eighth",   "Corchea con punto",             0.666),
    ("eighth",          "Corchea",                       0.5),
    ("triplet-eighth",  "Tresillo de corchea",           0.333),
    ("sixteenth",       "Semicorchea",                   0.25),
]

# Pulsos de negra para cada figura (independentes do tempo)
NOTE_BEATS = {
    4.0:   4.0,
    3.0:   3.0,
    2.0:   2.0,
    1.5:   1.5,
    1.0:   1.0,
    0.666: 2/3,
    0.5:   0.5,
    0.333: 1/3,
    0.25:  0.25,
}

# Mapa espello: invirte o índice en ALLOWED_RATIOS para rápido↔lento
_SORTED = sorted(ALLOWED_RATIOS)
MIRROR_MAP = {_SORTED[i]: _SORTED[-(i + 1)] for i in range(len(_SORTED))}


def mirror_ratio(r: float) -> float:
    """Devolve a razón espello de *r* invertendo o índice permitido."""
    return MIRROR_MAP.get(r, r)


# ---------------------------------------------------------------------------
# Axudas
# ---------------------------------------------------------------------------

def quantize_ratio(raw: float) -> float | None:
    """Axusta *raw* á razón musical permitida máis próxima se entra na tolerancia."""
    best, best_err = None, float("inf")
    for allowed in ALLOWED_RATIOS:
        err = abs(raw - allowed) / allowed
        if err < best_err:
            best, best_err = allowed, err
    if best_err <= RATIO_TOLERANCE:
        return best
    return None


def unique_onsets(notes: list[pretty_midi.Note]) -> list[float]:
    """Devolve os tempos de ataque ordenados e sen duplicados dunha lista de notas."""
    onsets = sorted({n.start for n in notes})
    merged: list[float] = []
    for t in onsets:
        if not merged or (t - merged[-1]) > ONSET_THRESHOLD:
            merged.append(t)
    return merged


def ratios_from_onsets(onsets: list[float]) -> list[float]:
    """Calcula os IOI e convérteos en razóns consecutivas cuantizadas."""
    if len(onsets) < 3:
        return []
    iois = [onsets[i + 1] - onsets[i] for i in range(len(onsets) - 1)]
    ratios: list[float] = []
    for i in range(1, len(iois)):
        if iois[i - 1] == 0:
            continue
        raw = iois[i] / iois[i - 1]
        q = quantize_ratio(raw)
        if q is not None:
            ratios.append(q)
    return ratios


# ---------------------------------------------------------------------------
# Construción da cadea de Markov
# ---------------------------------------------------------------------------

def _feed_midi(midi_path: str, chain, file_stats: list):
    """Analiza un MIDI e engade as súas razóns á *chain* recibida."""
    pm = pretty_midi.PrettyMIDI(midi_path)
    track_count = 0
    for inst in pm.instruments:
        if inst.is_drum or not inst.notes:
            continue
        onsets = unique_onsets(inst.notes)
        ratios = ratios_from_onsets(onsets)
        if len(ratios) < 3:
            continue
        track_count += 1
        for i in range(2, len(ratios)):
            state = (ratios[i - 2], ratios[i - 1])
            chain[state][ratios[i]] += 1
    file_stats.append({"path": midi_path, "name": os.path.basename(midi_path), "tracks": track_count})


def build_global_chain_from_folder(folder: str):
    """Procura todos os .mid de *folder* e crea unha cadea global.

    Devolve (contas_da_cadea, cadea_probabilidades, estatísticas_por_ficheiro).
    """
    midi_files = sorted(glob.glob(os.path.join(folder, "**", "*.mid"), recursive=True))
    chain: dict[tuple[float, float], dict[float, int]] = defaultdict(lambda: defaultdict(int))
    file_stats: list[dict] = []

    for mf in midi_files:
        _feed_midi(mf, chain, file_stats)

    chain = dict(chain)
    prob_chain = counts_to_probabilities(chain)
    return chain, prob_chain, file_stats


def counts_to_probabilities(chain):
    """Converte as contas brutas en {estado: [(razón, %, conta), ...]}."""
    prob_chain: dict[tuple[float, float], list[tuple[float, float, int]]] = {}
    for state, targets in chain.items():
        total = sum(targets.values())
        prob_chain[state] = [
            (ratio, round(count / total * 100, 2), count)
            for ratio, count in sorted(targets.items())
        ]
    return prob_chain


# ---------------------------------------------------------------------------
# Xeración da secuencia
# ---------------------------------------------------------------------------

def generate_sequence(
    chain: dict,
    start_state: tuple[float, float],
    length: int,
    noise_pct: float = 0.10,
    mirror: bool = False,
) -> tuple[list[float], list[bool]]:
    """Xera *length* eventos de razón a partir da cadea de Markov.

    Se *mirror* é True, a cadea escolle con normalidade pero a razón
    de saída reflíctese (rápido↔lento) antes de engadirse.
    O estado interno avanza co valor *orixinal* escollido, de maneira
    que se conserva o comportamento estatístico; só se invirte o
    resultado audible.

    Devolve (secuencia, marcas_de_ruído), onde noise_flags[i] vale True
    cando ese evento foi substituído por ruído aleatorio.
    """
    if start_state not in chain:
        start_state = random.choice(list(chain.keys()))

    sequence = [start_state[0], start_state[1]]
    noise_flags = [False, False]  # Os valores semente nunca son ruído
    state = start_state

    for _ in range(length):
        targets = chain.get(state)
        if not targets:
            state = random.choice(list(chain.keys()))
            fallback = state[0]
            sequence.append(mirror_ratio(fallback) if mirror else fallback)
            noise_flags.append(False)
            targets = chain.get(state)
            if not targets:
                continue
        ratios = list(targets.keys())
        weights = list(targets.values())
        chosen = random.choices(ratios, weights=weights, k=1)[0]

        # Ruído: cunha probabilidade noise_pct substitúese por unha razón aleatoria
        is_noise = random.random() < noise_pct
        if is_noise:
            chosen = random.choice(ALLOWED_RATIOS)

        # Modo espello: reflíctese a saída, pero o estado segue o valor orixinal
        output = mirror_ratio(chosen) if mirror else chosen

        sequence.append(output)
        noise_flags.append(is_noise)
        state = (state[1], chosen)  # Avanza co valor orixinal, non co espellado

    return sequence, noise_flags


def ratios_to_durations(ratios: list[float], base_dur: float = 0.5) -> list[float]:
    """Converte unha secuencia de razóns en duracións absolutas, en segundos."""
    durs = [base_dur]
    for r in ratios[1:]:
        durs.append(durs[-1] * r)
    return durs


def ratios_to_note_beats(ratios: list[float], first_note_ratio: float, second_note_ratio: float) -> list[float]:
    """Converte unha secuencia xerada en duracións expresadas en pulsos de negra.

    Os dous primeiros valores de *ratios* son o estado semente (r_{n-2}, r_{n-1}).
    *first_note_ratio* e *second_note_ratio* fixan as dúas primeiras duracións,
    e as razóns restantes aplícanse multiplicativamente.
    """
    beats = [NOTE_BEATS.get(first_note_ratio, 1.0),
             NOTE_BEATS.get(second_note_ratio, 1.0)]
    for r in ratios[2:]:
        beats.append(beats[-1] * r)
    return beats
