"""M4 - Foliada: votación pública + asignación de loops + modo de apagado.

Decisións do prompt orixinal:
  - Cada votante un voto, substitúe o seu anterior.
  - Empate -> aleatorio. Cero votos -> aleatorio (silenciosamente).
  - Loops asignados retíranse das opcións futuras.
  - Cando un loop comparte instrumentos co anterior, repártese 50/50 por SHA256(sid).
  - Apagado: cooldown = clamp(0.3, 1.0, 30·publico/musicos).
  - Supervisor server-forced asegura que se cumpre o ritmo esperado.
"""
import asyncio
import hashlib
import random
import time
from typing import Optional

from ..core.broadcaster import (
    to_admin, to_projection, to_public, to_directors,
    to_musician, to_musicians_by_base,
)
from ..data.loops import LOOPS, LOOP_COLORS, shared_instruments
from ..data.led_layout import section_for_loop
from ..data.dmx_mappings import LOOP_RGBW
from ..hardware.dmx_controller import dmx
from ..state import state
from ..logger import log


_voting_task: Optional[asyncio.Task] = None
_shutdown_task: Optional[asyncio.Task] = None
SHUTDOWN_HOLD_SECONDS = 10.0


# ---------------------------------------------------------------- VOTACIÓN ---

async def open_voting(seconds: int = 30):
    global _voting_task
    state.snap.movement = 4
    state.snap.voting_round += 1
    state.snap.voting_active = True
    state.snap.voting_ends_at = time.time() + seconds
    state.snap.votes_by_voter.clear()
    if not state.snap.available_loops:
        state.snap.available_loops = list(LOOPS.keys())
    choices = list(state.snap.available_loops)
    state.snap.voting_loop_choices = choices
    payload = {
        "round": state.snap.voting_round,
        "choices": choices,
        "colors": {k: LOOP_COLORS[k] for k in choices},
        "ends_at": state.snap.voting_ends_at,
        "seconds": seconds,
    }
    await to_public("m4:voting_open", payload)
    await to_admin("m4:voting_open", payload)
    await to_projection("m4:voting_open", payload)
    log.info(f"M4 votación aberta: round={state.snap.voting_round} choices={choices}")

    if _voting_task and not _voting_task.done():
        _voting_task.cancel()
    _voting_task = asyncio.create_task(_auto_close(seconds))


async def _auto_close(seconds: int):
    try:
        await asyncio.sleep(seconds)
        if state.snap.voting_active:
            await close_voting()
    except asyncio.CancelledError:
        pass


def cast_vote(public_sid: str, loop_id: str) -> bool:
    if not state.snap.voting_active:
        return False
    if loop_id not in state.snap.available_loops:
        return False
    state.snap.votes_by_voter[public_sid] = loop_id
    return True


def _tally() -> dict:
    counts: dict = {k: 0 for k in state.snap.available_loops}
    for v in state.snap.votes_by_voter.values():
        if v in counts:
            counts[v] += 1
    return counts


async def close_voting():
    if not state.snap.voting_active:
        return
    state.snap.voting_active = False
    counts = _tally()
    if not counts:
        return
    max_v = max(counts.values()) if counts else 0
    if max_v == 0:
        winner = random.choice(list(counts.keys()))
        log.info(f"M4 sen votos -> winner aleatorio silencioso = {winner}")
    else:
        ties = [k for k, v in counts.items() if v == max_v]
        winner = random.choice(ties)
    prev = state.snap.current_loop
    state.snap.current_loop = winner
    if winner in state.snap.available_loops:
        state.snap.available_loops.remove(winner)
    payload = {
        "winner": winner,
        "color": LOOP_COLORS.get(winner, "#ffffff"),
        "counts": counts,
        "prev": prev,
    }
    await to_public("m4:voting_close", payload)
    await to_admin("m4:voting_close", payload)
    await to_projection("m4:voting_close", payload)
    log.info(f"M4 winner={winner} prev={prev}")
    await assign_loop(winner, prev)


# ------------------------------------------------------- ASIGNACIÓN DE LOOP --

async def assign_loop(new_loop: str, prev_loop: Optional[str]):
    new_set = set(LOOPS[new_loop])
    prev_set = set(LOOPS[prev_loop]) if prev_loop else set()
    shared = new_set & prev_set
    color = LOOP_COLORS[new_loop]
    suffix = f"LOOP {new_loop[1:]}"

    # Snapshot de músicos baixo lock
    sessions = []
    for sid, ms in list(state.musicians.items()):
        sessions.append((sid, ms.base_instrument_id, ms.instrument_label))

    changers_by_base: dict = {}
    final_assignment: dict = {}  # base_id -> "change" | "stay"
    for base_id in new_set:
        members = [(sid, label) for sid, base, label in sessions if base == base_id]
        if not members:
            continue
        if base_id in shared and prev_loop is not None:
            for sid, label in members:
                bit = int(hashlib.sha256(sid.encode()).hexdigest(), 16) % 2
                if bit == 0:
                    final_assignment[sid] = ("change", base_id, label)
                else:
                    final_assignment[sid] = ("stay", base_id, label)
        else:
            for sid, label in members:
                final_assignment[sid] = ("change", base_id, label)

    # Notificar só aos que cambian (resolvendo socket_id desde cookie sid)
    for sid, (action, base_id, label) in final_assignment.items():
        if action == "change":
            ms = state.musicians.get(sid)
            if ms and ms.socket_id:
                await to_musician(ms.socket_id, "musician:play", {
                    "flash": True,
                    "color": color,
                    "label_suffix": suffix,
                    "loop": new_loop,
                    "playing": True,
                })

    # Director (nome + asignacións completas, ordenadas pola orde da orquesta)
    from ..data.instruments import CATALOG, CATALOG_BY_ID
    catalog_order = {inst.id: idx for idx, inst in enumerate(CATALOG)}
    sorted_assignments = sorted(
        final_assignment.items(),
        key=lambda kv: catalog_order.get(kv[1][1], 999),
    )
    await to_directors("director:update", {
        "event": "loop_changed",
        "loop": new_loop,
        "color": color,
        "instruments": sorted([CATALOG_BY_ID[bid].label for bid in new_set if bid in CATALOG_BY_ID],
                              key=lambda lbl: next((i for i, ins in enumerate(CATALOG) if ins.label == lbl), 999)),
        "assignments": [
            {"sid": sid, "instrument": fa[2], "action": fa[0]}
            for sid, fa in sorted_assignments
        ],
    })

    # Proxección
    await to_projection("m4:loop_assigned", {
        "loop": new_loop,
        "color": color,
        "instruments": list(new_set),
    })

    # DMX: prende a sección correspondente
    try:
        loop_index = int(new_loop[1:])
        leds = section_for_loop(loop_index)
        r, g, b, w = LOOP_RGBW[new_loop]
        for led in leds:
            dmx.universe.set_led(led, r, g, b, w)
    except Exception as e:
        log.warning(f"DMX loop section error: {e}")


# ---------------------------------------------------------------- APAGADO ---

async def start_shutdown_mode():
    global _shutdown_task
    musicos = max(1, len(state.musicians_alive()))
    publico = max(1, len(state.public_alive()))
    cooldown = max(0.3, min(1.0, 30.0 * publico / musicos))
    state.snap.shutdown_active = True
    state.snap.shutdown_cooldown = cooldown
    state.snap.shutdown_started_at = time.time()
    state.snap.shutdown_progressive_at = state.snap.shutdown_started_at + SHUTDOWN_HOLD_SECONDS
    now = time.time()
    for ps in state.public.values():
        ps.next_shutdown_allowed = now
    payload = {
        "cooldown": cooldown,
        "started_at": now,
        "progressive_starts_at": state.snap.shutdown_progressive_at,
    }
    await to_public("m4:shutdown_mode", payload)
    await to_admin("m4:shutdown_mode", payload)
    await to_projection("m4:shutdown_mode", payload)
    log.info(f"M4 apagado iniciado cooldown={cooldown:.2f}s")
    if _shutdown_task and not _shutdown_task.done():
        _shutdown_task.cancel()
    _shutdown_task = asyncio.create_task(_shutdown_supervisor())


async def _shutdown_supervisor():
    try:
        while state.snap.shutdown_active:
            await asyncio.sleep(2)
            if time.time() < state.snap.shutdown_progressive_at:
                continue
            elapsed = time.time() - state.snap.shutdown_started_at
            publico = max(1, len(state.public_alive()))
            expected_rate = publico / state.snap.shutdown_cooldown
            silenced_count = sum(1 for m in state.musicians.values() if m.silenced)
            expected = expected_rate * elapsed
            if silenced_count < expected - 1:
                alive = [s for s, m in state.musicians.items() if not m.silenced and not m.is_director]
                if alive:
                    target = random.choice(alive)
                    await silence_musician(target, by_public_sid=None, server_forced=True)
            alive = [s for s, m in state.musicians.items() if not m.silenced and not m.is_director]
            if not alive:
                state.snap.shutdown_active = False
                break
    except asyncio.CancelledError:
        pass


async def shutdown_click(public_sid: str) -> Optional[str]:
    if not state.snap.shutdown_active:
        return None
    ps = state.public.get(public_sid)
    if not ps:
        return None
    now = time.time()
    if now < state.snap.shutdown_progressive_at:
        return None
    if now < ps.next_shutdown_allowed:
        return None
    alive = [s for s, m in state.musicians.items() if not m.silenced and not m.is_director]
    if not alive:
        return None
    target = random.choice(alive)
    ps.next_shutdown_allowed = now + state.snap.shutdown_cooldown
    label = await silence_musician(target, by_public_sid=public_sid, server_forced=False)
    return label


async def silence_musician(musician_sid: str, by_public_sid: Optional[str], server_forced: bool) -> Optional[str]:
    ms = state.musicians.get(musician_sid)
    if not ms or ms.silenced:
        return None
    ms.silenced = True
    label = ms.instrument_label
    if ms.socket_id:
        await to_musician(ms.socket_id, "musician:play", {
            "flash": False, "color": "#000000", "label_suffix": "FIN", "playing": False,
        })
    if by_public_sid:
        ps = state.public.get(by_public_sid)
        if ps:
            ps.silenced_someone = True
    # Notificación a TODO o público de qué instrumento se acaba de apagar.
    await to_public("public:silenced", {"instrument": label, "forced": server_forced})
    # IP do público que disparou (informativa). Se foi server-forced, '—'.
    by_ip = "—"
    if by_public_sid:
        ps = state.public.get(by_public_sid)
        if ps and ps.ip:
            by_ip = ps.ip
    payload = {"instrument": label, "ip": by_ip, "forced": server_forced}
    await to_admin("m4:musician_off", payload)
    # Evento principal (feed pequeno na proxección, log no admin).
    await to_projection("m4:musician_off", payload)
    # Overlay grande con fade ~3s (texto = nome do instrumento).
    await to_projection("m4:musician_off_text", {
        "instrument": label,
        "forced": server_forced,
        "duration_ms": 3000,
    })
    log.info(f"M4 silenciado={label} forced={server_forced}")
    return label
