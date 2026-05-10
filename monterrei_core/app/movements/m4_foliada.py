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
from ..core.socket_server import sio
from ..data.loops import LOOPS, LOOP_COLORS, LOOP_SUBTITLES, shared_instruments
from ..data.led_layout import section_for_loop, led_for_instrument
from ..data.dmx_mappings import LOOP_RGBW
from ..hardware.dmx_controller import dmx
from ..state import state
from ..logger import log


_voting_task: Optional[asyncio.Task] = None
_shutdown_task: Optional[asyncio.Task] = None
# Tempo de gracia tras pulsar "Iniciar apagado" antes de que o sistema empece
# a forzar apagados se o público vai amodo. Após o splash de 5s no
# proxector, queremos que comece axiña -> 5s.
SHUTDOWN_HOLD_SECONDS = 5.0
# Duración máxima total do apagado supervisor normal.
MAX_SHUTDOWN_SECONDS = 20.0
# Duración total do apagado de emerxencia (desde que se preme o botón).
EMERGENCY_SHUTDOWN_SECONDS = 15.0
# Taxa máxima global de apagados activados polo público (apagados/segundo).
# Con ~60 músicos isto distribúe a extinción en ~20 s aínda que todo o
# público prime á vez. O supervisor segue funcionando en paralelo como
# garantía de ritmo mínimo.
SHUTDOWN_RATE = 3.0
SHUTDOWN_INTERVAL = 1.0 / SHUTDOWN_RATE   # ≈0.333 s entre slots

# Estado da cola de apagados (módulo-nivel, reinicializado en cada inicio).
_queue_task: Optional[asyncio.Task] = None
_shutdown_queue: Optional[asyncio.Queue] = None
_queued_sids: set = set()             # public_sids en cola (evita duplicados)
_next_shutdown_token_at: float = 0.0  # cursor temporal do rate-limit (asyncio-safe)


# ---------------------------------------------------------------- VOTACIÓN ---

async def open_voting(seconds: int = 15):
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
    cur = state.snap.current_loop
    # Loops xa saídos en votacións previas (exclúe o actual).
    past_loops = [k for k in state.snap.played_loops if k != cur]
    payload = {
        "round": state.snap.voting_round,
        "choices": choices,
        "colors": {k: LOOP_COLORS[k] for k in choices},
        "ends_at": state.snap.voting_ends_at,
        "seconds": seconds,
        "current_loop": cur,
        "current_color": LOOP_COLORS.get(cur) if cur else None,
        "current_subtitle": LOOP_SUBTITLES.get(cur) if cur else None,
        "past_loops": [
            {
                "loop": k,
                "color": LOOP_COLORS.get(k, "#ffffff"),
                "subtitle": LOOP_SUBTITLES.get(k, ""),
            }
            for k in past_loops
        ],
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
    # Histórico de loops xa saídos (orde de aparición).
    if winner not in state.snap.played_loops:
        state.snap.played_loops.append(winner)
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
        "subtitle": LOOP_SUBTITLES.get(new_loop, ""),
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

    # DMX por-músico: acende o LED de cada músico que toca o novo loop
    # (cor do loop). Os músicos que xa tocaban quedan iguais; os apagados
    # non se tocan.
    try:
        r, g, b, w = LOOP_RGBW[new_loop]
        for sid, (action, base_id, _label) in final_assignment.items():
            ms = state.musicians.get(sid)
            if not ms or ms.silenced:
                continue
            led = led_for_instrument(base_id)
            if led is not None:
                dmx.universe.set_led(led, r, g, b, w)
    except Exception as e:
        log.warning(f"DMX per-musician loop error: {e}")


# ---------------------------------------------------------------- APAGADO ---

def _reset_shutdown_queue():
    """Reinicia a cola de apagados con taxa limitada (chama en cada inicio)."""
    global _shutdown_queue, _queued_sids, _next_shutdown_token_at
    _shutdown_queue = asyncio.Queue()
    _queued_sids = set()
    _next_shutdown_token_at = 0.0


async def _drain_remaining_queue():
    """Notifica a tódolos usuarios pendentes en cola que o apagado rematou."""
    if _shutdown_queue is None:
        return
    drained: list = []
    while True:
        try:
            drained.append(_shutdown_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    for public_sid, _ in drained:
        if public_sid not in _queued_sids:
            continue
        _queued_sids.discard(public_sid)
        ps = state.public.get(public_sid)
        if ps and ps.socket_id:
            await sio.emit(
                "shutdown_executed",
                {"instrument": None},
                to=ps.socket_id,
                namespace="/public",
            )


async def _shutdown_queue_processor():
    """Drena a cola de pedidos de apagado ao ritmo de SHUTDOWN_RATE/segundo.

    - Cada usuario que chega cando o token está saturado queda en cola.
    - Recíbe "shutdown_executed" cando o seu apagado se executa.
    - Se non quedan músicos vivos, notifíca a todos os pendentes e sáe.
    """
    try:
        while state.snap.shutdown_active:
            try:
                item = await asyncio.wait_for(_shutdown_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            public_sid, scheduled_at = item
            if public_sid not in _queued_sids:
                # Slot invalidado (p.ex. reset / emerxencia).
                continue
            _queued_sids.discard(public_sid)

            # Esperar ata o instante reservado para este slot.
            wait = scheduled_at - time.time()
            if wait > 0.0:
                await asyncio.sleep(wait)

            if not state.snap.shutdown_active:
                # Apagado cancelado mentres agardabamos: reénchese o usuario.
                ps = state.public.get(public_sid)
                if ps and ps.socket_id:
                    await sio.emit(
                        "shutdown_executed",
                        {"instrument": None},
                        to=ps.socket_id,
                        namespace="/public",
                    )
                break

            alive = [
                s for s, m in state.musicians.items()
                if not m.silenced and not m.is_director
            ]
            if not alive:
                # Xa non quedan músicos: notificar e drenar o resto da cola.
                ps = state.public.get(public_sid)
                if ps and ps.socket_id:
                    await sio.emit(
                        "shutdown_executed",
                        {"instrument": None},
                        to=ps.socket_id,
                        namespace="/public",
                    )
                await _drain_remaining_queue()
                break

            target = random.choice(alive)
            instrument_label = await silence_musician(
                target, by_public_sid=public_sid, server_forced=False
            )

            # Notificar persoalmente ao usuario que o seu apagado se executou.
            ps = state.public.get(public_sid)
            if ps and ps.socket_id:
                await sio.emit(
                    "shutdown_executed",
                    {"instrument": instrument_label},
                    to=ps.socket_id,
                    namespace="/public",
                )

    except asyncio.CancelledError:
        pass


async def start_shutdown_mode():
    global _shutdown_task, _queue_task
    musicos = max(1, len(state.musicians_alive()))
    publico = max(1, len(state.public_alive()))
    cooldown = max(0.3, min(1.0, 30.0 * publico / musicos))
    state.snap.shutdown_active = True
    state.snap.shutdown_cooldown = cooldown
    now = time.time()
    state.snap.shutdown_started_at = now
    state.snap.shutdown_progressive_at = now + SHUTDOWN_HOLD_SECONDS
    # Reiniciar a cola de apagados con taxa global limitada.
    _reset_shutdown_queue()
    payload = {
        "cooldown": cooldown,
        "started_at": now,
        "progressive_starts_at": state.snap.shutdown_progressive_at,
    }
    await to_public("m4:shutdown_mode", payload)
    await to_admin("m4:shutdown_mode", payload)
    await to_projection("m4:shutdown_mode", payload)
    # Contador inicial de músicos vivos para a UI da proxección.
    try:
        alive_count = len(state.musicians_alive())
    except Exception:
        alive_count = 0
    await to_projection("projection:musicians_alive", {"count": alive_count})
    await to_admin("admin:musicians_alive", {"count": alive_count})
    log.info(f"M4 apagado iniciado cooldown={cooldown:.2f}s rate={SHUTDOWN_RATE}/s")
    # Procesador da cola de apagados (taxa limitada).
    if _queue_task and not _queue_task.done():
        _queue_task.cancel()
    _queue_task = asyncio.create_task(_shutdown_queue_processor())
    # Supervisor de forzado: garante o ritmo mínimo de extinción.
    if _shutdown_task and not _shutdown_task.done():
        _shutdown_task.cancel()
    _shutdown_task = asyncio.create_task(_shutdown_supervisor())


async def _shutdown_supervisor(max_seconds: float = MAX_SHUTDOWN_SECONDS):
    try:
        while state.snap.shutdown_active:
            await asyncio.sleep(0.4)
            now = time.time()
            if now < state.snap.shutdown_progressive_at:
                continue
            elapsed = now - state.snap.shutdown_started_at
            alive = [s for s, m in state.musicians.items() if not m.silenced and not m.is_director]
            if not alive:
                state.snap.shutdown_active = False
                break
            # Tras max_seconds forézase TODO rapidamente.
            if elapsed >= max_seconds:
                target = random.choice(alive)
                await silence_musician(target, by_public_sid=None, server_forced=True)
                # Burst final: 0.15s entre apagados.
                await asyncio.sleep(0.15)
                continue
            # Progresivo: canto máis preto de max_seconds, máis agresivo o forzado.
            t_window = max(0.001, max_seconds - SHUTDOWN_HOLD_SECONDS)
            phase = max(0.0, min(1.0, (elapsed - SHUTDOWN_HOLD_SECONDS) / t_window))
            publico = max(1, len(state.public_alive()))
            base_rate = publico / state.snap.shutdown_cooldown
            expected_rate = base_rate * (1.0 + phase)
            silenced_count = sum(1 for m in state.musicians.values() if m.silenced)
            expected = expected_rate * elapsed
            if silenced_count < expected - 1:
                target = random.choice(alive)
                await silence_musician(target, by_public_sid=None, server_forced=True)
    except asyncio.CancelledError:
        pass


async def start_emergency_shutdown():
    """Apaga aleatoriamente tódolos músicos restantes nun máximo de 15s.

    Pode chamarse tanto se o modo apagado xa está activo como se non.
    Non precisa cooldown nin interacción do público: é o servidor quen
    silencia directamente. Resetea o reloxo interno para que os 15s
    empecen a contar desde este momento. Cancela a cola de apagados
    do público para evitar conflitos co supervisor de emerxencia.
    """
    global _shutdown_task, _queue_task
    if not state.snap.shutdown_active:
        # Activar o modo apagado básico se non estaba xa iniciado
        await start_shutdown_mode()
    # Cancelar e limpar a cola de apagados do público.
    if _queue_task and not _queue_task.done():
        _queue_task.cancel()
    _reset_shutdown_queue()
    # Resetear o temporizador: os EMERGENCY_SHUTDOWN_SECONDS empezan agora.
    now = time.time()
    state.snap.shutdown_started_at = now
    state.snap.shutdown_progressive_at = now  # Sen período de gracia
    log.info("M4 apagado de emerxencia: supervisor 15s iniciado")
    await to_admin("m4:emergency_shutdown", {"duration_ms": int(EMERGENCY_SHUTDOWN_SECONDS * 1000)})
    if _shutdown_task and not _shutdown_task.done():
        _shutdown_task.cancel()
    _shutdown_task = asyncio.create_task(
        _shutdown_supervisor(max_seconds=EMERGENCY_SHUTDOWN_SECONDS)
    )


async def shutdown_click(public_sid: str) -> dict:
    """Procesa un pedido de apagado dun usuario do público.

    Retorna un dict con chave 'status':
      - 'executed':       apagado inmediato, 'instrument' co nome.
      - 'queued':         engadido á cola, 'position' coa posición (1-based).
      - 'already_queued': xa estaba en cola, 'position' actual.
      - 'rejected':       non posible, 'reason' coa causa.

    O sistema garaínza un máximo global de SHUTDOWN_RATE apagados/segundo
    independentemente de cantos usuarios priman á vez.
    """
    global _next_shutdown_token_at

    if not state.snap.shutdown_active:
        return {"status": "rejected", "reason": "not_active"}
    ps = state.public.get(public_sid)
    if not ps:
        return {"status": "rejected", "reason": "no_session"}
    now = time.time()
    if now < state.snap.shutdown_progressive_at:
        return {"status": "rejected", "reason": "hold"}

    alive = [
        s for s, m in state.musicians.items()
        if not m.silenced and not m.is_director
    ]
    if not alive:
        return {"status": "rejected", "reason": "none_alive"}

    # Xa en cola: informar posición sen añadir de novo.
    if public_sid in _queued_sids:
        pos = (_shutdown_queue.qsize() if _shutdown_queue else 0) or 1
        return {"status": "already_queued", "position": pos}

    # Reservar slot temporal (atómico: non hai `await` entre lectura e escritura).
    scheduled_at = max(now, _next_shutdown_token_at)
    _next_shutdown_token_at = scheduled_at + SHUTDOWN_INTERVAL

    if scheduled_at <= now:
        # Token libre: executar de inmediato.
        target = random.choice(alive)
        label = await silence_musician(target, by_public_sid=public_sid, server_forced=False)
        return {"status": "executed", "instrument": label}

    # Token no futuro: poñer en cola e notificar ao usuario.
    if _shutdown_queue is None:
        # Non debería ocorrer, pero por seguridade.
        return {"status": "rejected", "reason": "queue_unavailable"}
    _queued_sids.add(public_sid)
    await _shutdown_queue.put((public_sid, scheduled_at))
    pos = _shutdown_queue.qsize()
    return {"status": "queued", "position": pos}


async def silence_musician(musician_sid: str, by_public_sid: Optional[str], server_forced: bool) -> Optional[str]:
    ms = state.musicians.get(musician_sid)
    if not ms or ms.silenced:
        return None
    ms.silenced = True
    label = ms.instrument_label
    # DMX: apaga o LED dese músico
    try:
        led = led_for_instrument(ms.base_instrument_id)
        if led is not None:
            with dmx._lock:
                dmx.universe.set_led(led, 0, 0, 0, 0)
    except Exception:
        pass
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
    # Engade contador de músicos vivos para a UI (proxección / admin).
    try:
        alive_count = len(state.musicians_alive())
    except Exception:
        alive_count = 0
    await to_projection("projection:musicians_alive", {"count": alive_count})
    await to_admin("admin:musicians_alive", {"count": alive_count})
    return label
