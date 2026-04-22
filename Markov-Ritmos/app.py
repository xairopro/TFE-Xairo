#!/usr/bin/env python3
"""
Interface web con Flask para o xerador rítmico baseado en cadeas de Markov.

Execución: python app.py
Acceso:   http://127.0.0.1:5000
"""

import json
import os
import subprocess
import uuid

from flask import Flask, jsonify, render_template, request, send_from_directory
import pretty_midi

from markov_rhythm import (
    ALLOWED_RATIOS,
    MIRROR_MAP,
    NOTE_BEATS,
    NOTE_NAMES,
    RATIO_LABEL,
    build_global_chain_from_folder,
    generate_sequence,
    mirror_ratio,
    ratios_to_note_beats,
)

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MIDI_FOLDER = os.path.join(BASE_DIR, "Flows desde Muiñeira de Monterrei")
STATIC_DIR = os.path.join(BASE_DIR, "static")
SCORE_DIR = os.path.join(STATIC_DIR, "scores")
MUSESCORE = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"

os.makedirs(SCORE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Construír a cadea ao iniciar a aplicación
# ---------------------------------------------------------------------------
print("Construíndo a cadea global de Markov a partir dos ficheiros MIDI…")
CHAIN, PROB_CHAIN, FILE_STATS = build_global_chain_from_folder(MIDI_FOLDER)
total_tracks = sum(f["tracks"] for f in FILE_STATS)
print(f"  → {len(FILE_STATS)} ficheiros, {total_tracks} pistas, {len(CHAIN)} estados.")

# ---------------------------------------------------------------------------
# Preparar a matriz de probabilidades para a táboa
# (estado → {razón: (porcentaxe, conta)})
# ---------------------------------------------------------------------------
# Recolle todas as razóns que aparecen realmente como destino
ALL_TARGET_RATIOS = sorted({r for targets in PROB_CHAIN.values() for r, _, _ in targets})

MATRIX_ROWS = []  # Lista de dicionarios lista para a plantilla
for state in sorted(PROB_CHAIN.keys()):
    lbl = (RATIO_LABEL.get(state[0], str(state[0])),
           RATIO_LABEL.get(state[1], str(state[1])))
    targets = PROB_CHAIN[state]
    tmap = {r: (pct, cnt) for r, pct, cnt in targets}
    total_examples = sum(cnt for _, _, cnt in targets)
    row = {
        "state": state,
        "label": lbl,
        "cells": {r: tmap.get(r, (0, 0)) for r in ALL_TARGET_RATIOS},
        "total": total_examples,
    }
    MATRIX_ROWS.append(row)

# ---------------------------------------------------------------------------
# Aplicación Flask
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=STATIC_DIR)


@app.route("/")
def index():
    return render_template(
        "index.html",
        file_stats=FILE_STATS,
        total_tracks=total_tracks,
        n_states=len(CHAIN),
        note_names=NOTE_NAMES,
        allowed=ALLOWED_RATIOS,
        ratio_label=RATIO_LABEL,
        matrix_rows=MATRIX_ROWS,
        target_ratios=ALL_TARGET_RATIOS,
    )


@app.route("/generate", methods=["POST"])
def generate():
    import random as _rnd
    data = request.get_json(force=True)
    # A persoa usuaria escolle figuras; o front-end envía os valores de razón
    r1 = float(data.get("r1", 1.0))
    r2 = float(data.get("r2", 1.0))
    length = int(data.get("length", 16))
    length = max(1, min(length, 200))
    seed = int(data.get("seed", 42))
    mirror = bool(data.get("mirror", False))
    _rnd.seed(seed)

    start = (r1, r2)
    seq, noise_flags = generate_sequence(CHAIN, start, length, mirror=mirror)
    beats = ratios_to_note_beats(seq, r1, r2)
    mode_label = "Modo espello" if mirror else "Modo normal"

    # Preparar as etiquetas de figura para a vista
    note_labels = [_beats_to_label(b) for b in beats]

    # Xerar a partitura con MuseScore nun pentagrama de percusión dunha liña
    score_url = None
    pdf_url = None
    try:
        score_url, pdf_url = _render_score(beats, noise_flags, seed, mode_label)
    except Exception as exc:
        print(f"Fallou a xeración con MuseScore: {exc}")

    return jsonify(
        ratios=[RATIO_LABEL.get(r, str(r)) for r in seq],
        note_labels=note_labels,
        beats=[round(b, 4) for b in beats],
        noise=noise_flags,
        score_url=score_url,
        pdf_url=pdf_url,
        mirror=mirror,
    )


@app.route("/static/scores/<path:filename>")
def serve_score(filename):
    return send_from_directory(SCORE_DIR, filename)


# ---------------------------------------------------------------------------
# Axudas – pulsos ↔ nomes de figura
# ---------------------------------------------------------------------------

_BEAT_LABEL = {
    4.0:   "Redonda",
    3.0:   "Branca con punto",
    2.0:   "Branca",
    1.5:   "Negra con punto",
    1.0:   "Negra",
    2/3:   "Corchea con punto",
    0.5:   "Corchea",
    1/3:   "Tresillo de corchea",
    0.25:  "Semicorchea",
}

def _beats_to_label(b: float) -> str:
    """Devolve o nome de figura máis próximo para *b* pulsos de negra."""
    best_name, best_err = "?", float("inf")
    for ref, name in _BEAT_LABEL.items():
        err = abs(b - ref)
        if err < best_err:
            best_err = err
            best_name = name
    return best_name


# ---------------------------------------------------------------------------
# MusicXML → PNG con MuseScore (percusión nunha soa liña)
# ---------------------------------------------------------------------------

def _beats_to_musicxml(beat_dur: float):
    """Converte unha duración en pulsos a (tipo, con_punto, ticks_division).

    Empregamos 12 divisións por negra para permitir tresillos.
    """
    divisions = 12
    table = [
        (0.25,  "16th",    False, 3),
        (1/3,   "eighth",  False, 4),    # corchea de tresillo
        (0.5,   "eighth",  False, 6),
        (2/3,   "eighth",  True,  8),    # corchea con punto
        (1.0,   "quarter", False, 12),
        (1.5,   "quarter", True,  18),
        (2.0,   "half",    False, 24),
        (3.0,   "half",    True,  36),
        (4.0,   "whole",   False, 48),
    ]
    best_type, best_dot, best_dur = "quarter", False, 12
    best_err = float("inf")
    for ref, tname, dot, ticks in table:
        err = abs(beat_dur - ref)
        if err < best_err:
            best_err = err
            best_type, best_dot, best_dur = tname, dot, ticks
    return best_type, best_dot, best_dur


# ---------------------------------------------------------------------------
# Axudas para separar compases mantendo ligaduras correctas
# ---------------------------------------------------------------------------

_TICK_TYPE_TABLE = {
    3: ("16th", False),
    4: ("eighth", False),
    6: ("eighth", False),
    8: ("eighth", True),
    12: ("quarter", False),
    18: ("quarter", True),
    24: ("half", False),
    36: ("half", True),
    48: ("whole", False),
}


def _ticks_to_xml_type(ticks):
    """Asocia ticks co par máis próximo (tipo MusicXML, con punto)."""
    if ticks in _TICK_TYPE_TABLE:
        return _TICK_TYPE_TABLE[ticks]
    best = min(_TICK_TYPE_TABLE, key=lambda k: abs(k - ticks))
    return _TICK_TYPE_TABLE[best]


def _decompose_ticks(total):
    """Descompón *total* ticks nunha lista de duracións válidas.

    Se aparecen casos raros (1, 2 ou 5 ticks) que non se poden expresar
    como suma de figuras estándar, aproxímaos ao valor válido máis próximo.
    """
    if total <= 0:
        return []
    if total in _TICK_TYPE_TABLE:
        return [total]
    valid = sorted(_TICK_TYPE_TABLE, reverse=True)
    cache: dict = {}

    def _solve(n):
        if n <= 0:
            return []
        if n in cache:
            return cache[n]
        if n in _TICK_TYPE_TABLE:
            cache[n] = [n]
            return [n]
        for v in valid:
            if v < n:
                rest = _solve(n - v)
                if rest is not None:
                    cache[n] = [v] + rest
                    return cache[n]
        cache[n] = None
        return None

    result = _solve(total)
    if result is not None:
        return result
    # Arredondar os restos raros que non admiten descomposición exacta
    rounded = min(v for v in sorted(_TICK_TYPE_TABLE) if v >= total)
    return [rounded]


def _split_into_measures(beats, measure_ticks=36):
    """Parte as figuras en compases, engadindo ligaduras nos límites.

    Devolve unha lista de compases; cada compás contén eventos cos campos
    *idx*, *ticks*, *tie_start* e *tie_stop*.
    """
    ticks_list = [_beats_to_musicxml(b)[2] for b in beats]
    events: list[dict] = []
    pos = 0

    for i, note_ticks in enumerate(ticks_list):
        note_end = pos + note_ticks
        bar_s = pos // measure_ticks
        bar_e = ((note_end - 1) // measure_ticks) if note_ticks > 0 else bar_s

        if bar_s == bar_e:
            events.append({"idx": i, "ticks": note_ticks,
                           "tie_start": False, "tie_stop": False})
        else:
            # Recolle os fragmentos aliñados coas barras de compás
            cursor, fragments = pos, []
            while cursor < note_end:
                nxt = ((cursor // measure_ticks) + 1) * measure_ticks
                fragments.append(min(note_end, nxt) - cursor)
                cursor = min(note_end, nxt)
            # Converte cada fragmento en eventos, descompoñendo se fai falta
            for fi, frag in enumerate(fragments):
                sub = _decompose_ticks(frag)
                for si, sp in enumerate(sub):
                    first = (fi == 0 and si == 0)
                    last = (fi == len(fragments) - 1
                            and si == len(sub) - 1)
                    events.append({"idx": i, "ticks": sp,
                                   "tie_start": not last,
                                   "tie_stop": not first})
        pos = note_end

    # Agrupar os eventos por compases
    measures: list[list[dict]] = []
    cur: list[dict] = []
    remaining = measure_ticks
    for evt in events:
        t = evt["ticks"]
        if t > remaining and cur:
            measures.append(cur)
            cur, remaining = [], measure_ticks
        cur.append(evt)
        remaining -= t
        if remaining <= 0:
            measures.append(cur)
            cur, remaining = [], measure_ticks
    if cur:
        measures.append(cur)
    return measures


def _render_score(beats: list[float], noise_flags: list[bool], seed: int = 42,
                  mode_label: str = "Modo normal") -> str | None:
    """Escribe un MusicXML de percusión sen altura e devolve a URL xerada."""
    uid = uuid.uuid4().hex[:10]
    xml_path = os.path.join(SCORE_DIR, f"{uid}.musicxml")
    png_path = os.path.join(SCORE_DIR, f"{uid}.png")

    divisions = 12
    measure_ticks = 36
    measures = _split_into_measures(beats, measure_ticks)

    measures_xml = []
    for m_num, m_events in enumerate(measures, 1):
        attr = ""
        if m_num == 1:
            attr = f"""      <attributes>
        <divisions>{divisions}</divisions>
        <time>
          <beats>6</beats>
          <beat-type>8</beat-type>
        </time>
        <clef>
          <sign>percussion</sign>
        </clef>
        <staff-details>
          <staff-lines>1</staff-lines>
        </staff-details>
      </attributes>
"""
        notes = []
        for evt in m_events:
            ticks = evt["ticks"]
            ntype, dotted = _ticks_to_xml_type(ticks)
            dot_tag = "\n        <dot/>" if dotted else ""
            idx = evt["idx"]
            is_noise = noise_flags[idx] if idx < len(noise_flags) else False
            color = ' color="#FF0000"' if is_noise else ''

            tie_tags = ""
            if evt["tie_stop"]:
                tie_tags += '\n        <tie type="stop"/>'
            if evt["tie_start"]:
                tie_tags += '\n        <tie type="start"/>'

            notation_parts = []
            if evt["tie_stop"]:
                notation_parts.append('          <tied type="stop"/>')
            if evt["tie_start"]:
                notation_parts.append('          <tied type="start"/>')
            notations = ""
            if notation_parts:
                notations = ("\n        <notations>\n"
                             + "\n".join(notation_parts)
                             + "\n        </notations>")

            notes.append(
                f"""      <note{color}>
        <unpitched>
          <display-step>E</display-step>
          <display-octave>4</display-octave>
        </unpitched>
        <duration>{ticks}</duration>{tie_tags}
        <type>{ntype}</type>{dot_tag}
        <stem>up</stem>
        <notehead{color}>normal</notehead>{notations}
      </note>"""
            )

        body = "\n".join(notes)
        measures_xml.append(
            f'    <measure number="{m_num}">\n{attr}{body}\n    </measure>'
        )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN"
  "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <work>
    <work-title>Ritmos de Markov</work-title>
  </work>
  <identification>
    <creator type="composer">Xairo Campos Blanco</creator>
            <creator type="lyricist">Semente: {seed} \u2014 {mode_label}</creator>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Ritmo</part-name>
      <score-instrument id="P1-I1">
        <instrument-name>Percusi\u00f3n</instrument-name>
      </score-instrument>
    </score-part>
  </part-list>
  <part id="P1">
{chr(10).join(measures_xml)}
  </part>
</score-partwise>
"""
    with open(xml_path, "w") as f:
        f.write(xml)

    try:
        subprocess.run(
            [MUSESCORE, "-o", png_path, xml_path],
            timeout=30,
            capture_output=True,
        )
    except FileNotFoundError:
        print("MuseScore non está dispoñible; omítese a xeración da partitura.")
        return None, None

    # Exportar tamén en PDF
    pdf_path = os.path.join(SCORE_DIR, f"{uid}.pdf")
    try:
        subprocess.run(
            [MUSESCORE, "-o", pdf_path, xml_path],
            timeout=30,
            capture_output=True,
        )
    except FileNotFoundError:
        pass

    png_url = None
    candidates = [png_path, png_path.replace(".png", "-1.png")]
    for c in candidates:
        if os.path.exists(c):
            png_url = f"/static/scores/{os.path.basename(c)}"
            break

    pdf_url = f"/static/scores/{uid}.pdf" if os.path.exists(pdf_path) else None
    return png_url, pdf_url


# ---------------------------------------------------------------------------
# Aplicar duracións de Markov a un MIDI con alturas
# ---------------------------------------------------------------------------

def _extract_pitches_from_midi(midi_data: bytes) -> list[int]:
    """Le un MIDI e devolve as alturas na orde dos ataques, sen usar duracións."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        tmp.write(midi_data)
        tmp_path = tmp.name
    try:
        pm = pretty_midi.PrettyMIDI(tmp_path)
    finally:
        os.unlink(tmp_path)
    notes = []
    for inst in pm.instruments:
        for n in inst.notes:
            notes.append((n.start, n.pitch))
    notes.sort(key=lambda x: x[0])
    return [p for _, p in notes]


# Axudas de alturas para MusicXML
_PITCH_NAMES = ['C', 'C', 'D', 'D', 'E', 'F', 'F', 'G', 'G', 'A', 'A', 'B']
_PITCH_ALTER = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]


def _render_pitched_score(pitches: list[int], beats: list[float],
                          noise_flags: list[bool], seed: int = 42,
                          mode_label: str = "Modo normal"):
    """Crea un MusicXML con alturas sobre pentagrama de cinco liñas en 6/8."""
    uid = uuid.uuid4().hex[:10]
    xml_path = os.path.join(SCORE_DIR, f"pitched_{uid}.musicxml")
    png_path = os.path.join(SCORE_DIR, f"pitched_{uid}.png")

    divisions = 12
    measure_ticks = 36

    n = len(beats)
    if not pitches:
        return None, None
    extended_pitches = [pitches[i % len(pitches)] for i in range(n)]

    measures = _split_into_measures(beats, measure_ticks)

    measures_xml = []
    for m_num, m_events in enumerate(measures, 1):
        attr = ""
        if m_num == 1:
            attr = f"""      <attributes>
        <divisions>{divisions}</divisions>
        <time>
          <beats>6</beats>
          <beat-type>8</beat-type>
        </time>
        <clef>
          <sign>G</sign>
          <line>2</line>
        </clef>
      </attributes>
"""
        notes = []
        for evt in m_events:
            ticks = evt["ticks"]
            ntype, dotted = _ticks_to_xml_type(ticks)
            dot_tag = "\n        <dot/>" if dotted else ""
            idx = evt["idx"]
            is_noise = noise_flags[idx] if idx < len(noise_flags) else False
            color = ' color="#FF0000"' if is_noise else ''

            midi_pitch = extended_pitches[idx % len(extended_pitches)]
            step = _PITCH_NAMES[midi_pitch % 12]
            alter = _PITCH_ALTER[midi_pitch % 12]
            octave = (midi_pitch // 12) - 1

            alter_tag = f"\n          <alter>{alter}</alter>" if alter != 0 else ""
            accidental_tag = ""
            if alter == 1 and not evt["tie_stop"]:
                acc_color = ' color="#FF0000"' if is_noise else ''
                accidental_tag = f"\n        <accidental{acc_color}>sharp</accidental>"

            tie_tags = ""
            if evt["tie_stop"]:
                tie_tags += '\n        <tie type="stop"/>'
            if evt["tie_start"]:
                tie_tags += '\n        <tie type="start"/>'

            notation_parts = []
            if evt["tie_stop"]:
                notation_parts.append('          <tied type="stop"/>')
            if evt["tie_start"]:
                notation_parts.append('          <tied type="start"/>')
            notations = ""
            if notation_parts:
                notations = ("\n        <notations>\n"
                             + "\n".join(notation_parts)
                             + "\n        </notations>")

            notes.append(
                f"""      <note{color}>
        <pitch>
          <step>{step}</step>{alter_tag}
          <octave>{octave}</octave>
        </pitch>
        <duration>{ticks}</duration>{tie_tags}
        <type>{ntype}</type>{dot_tag}
        <stem>up</stem>{accidental_tag}{notations}
      </note>"""
            )

        body = "\n".join(notes)
        measures_xml.append(
            f'    <measure number="{m_num}">\n{attr}{body}\n    </measure>'
        )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN"
  "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <work>
    <work-title>Ritmos de Markov con alturas</work-title>
  </work>
  <identification>
    <creator type="composer">Xairo Campos Blanco</creator>
        <creator type="lyricist">Semente: {seed} \u2014 {mode_label}</creator>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Melodía</part-name>
    </score-part>
  </part-list>
  <part id="P1">
{chr(10).join(measures_xml)}
  </part>
</score-partwise>
"""
    with open(xml_path, "w") as f:
        f.write(xml)

    try:
        subprocess.run(
            [MUSESCORE, "-o", png_path, xml_path],
            timeout=30, capture_output=True,
        )
    except FileNotFoundError:
        return None, None

    pdf_path = os.path.join(SCORE_DIR, f"pitched_{uid}.pdf")
    try:
        subprocess.run(
            [MUSESCORE, "-o", pdf_path, xml_path],
            timeout=30, capture_output=True,
        )
    except FileNotFoundError:
        pass

    png_url = None
    candidates = [png_path, png_path.replace(".png", "-1.png")]
    for c in candidates:
        if os.path.exists(c):
            png_url = f"/static/scores/{os.path.basename(c)}"
            break

    pdf_url = f"/static/scores/pitched_{uid}.pdf" if os.path.exists(pdf_path) else None
    return png_url, pdf_url


@app.route("/apply-pitches", methods=["POST"])
def apply_pitches():
    """Recibe un MIDI e os pulsos actuais para xerar a partitura con alturas."""
    midi_file = request.files.get("midi")
    if not midi_file:
        return jsonify(error="Non se recibiu ningún ficheiro MIDI."), 400

    beats = json.loads(request.form.get("beats", "[]"))
    noise_flags = json.loads(request.form.get("noise", "[]"))
    seed = int(request.form.get("seed", 42))
    mode_label = request.form.get("mode_label", "Modo normal")

    if not beats:
        return jsonify(error="Primeiro xera un ritmo de Markov."), 400

    midi_data = midi_file.read()
    try:
        pitches = _extract_pitches_from_midi(midi_data)
    except Exception as exc:
        return jsonify(error=f"Erro ao ler o MIDI: {exc}"), 400

    if not pitches:
        return jsonify(error="Non se atoparon notas no ficheiro MIDI."), 400

    try:
        score_url, pdf_url = _render_pitched_score(pitches, beats, noise_flags, seed, mode_label)
    except Exception as exc:
        return jsonify(error=f"Erro ao renderizar: {exc}"), 500

    return jsonify(score_url=score_url, pdf_url=pdf_url)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False, port=5000)
