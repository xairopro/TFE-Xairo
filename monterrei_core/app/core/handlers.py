"""Handlers Socket.IO en todos os namespaces."""
from __future__ import annotations
import time

from .socket_server import sio
from .session_manager import register_musician, register_public, musician_snapshot, public_snapshot, disconnect
from .broadcaster import to_admin, to_projection
from ..state import state
from ..data.instruments import CATALOG, CATALOG_BY_ID, assign_unique_id, base_id_of
from ..data.loops import LOOP_COLORS, LOOPS
from ..data.groups import GROUPS
from ..logger import logger
from ..movements import m1_video, m2_lorenz, m3_markov, m4_foliada
from ..effects.color_engine import color_engine


def _client_ip(environ) -> str:
    """Extrae IP do cliente do environ ASGI."""
    if not environ:
        return ""
    xff = environ.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return environ.get("REMOTE_ADDR", "") or ""


# ---------- /musician (músicos + director) ------------------

@sio.on("connect", namespace="/musician")
async def m_connect(sid, environ, auth):
    cookie_sid = (auth or {}).get("sid")
    logger.debug(f"musician connect socket={sid} cookie_sid={cookie_sid}")
    ip = _client_ip(environ)
    if cookie_sid and cookie_sid in state.musicians:
        with state.lock:
            state.musicians[cookie_sid].socket_id = sid
            state.musicians[cookie_sid].last_seen = time.time()
            if ip:
                state.musicians[cookie_sid].ip = ip
        await sio.emit("state:restore", musician_snapshot(cookie_sid) or {},
                       to=sid, namespace="/musician")
    # Envíalle catálogo + reconto por base id (cantos hai xa nese instrumento)
    occupied_count: dict[str, int] = {}
    for m in state.musicians.values():
        b = m.base_instrument_id
        occupied_count[b] = occupied_count.get(b, 0) + 1
    await sio.emit("catalog", {
        "instruments": [{"id": i.id, "label": i.label, "section": i.section} for i in CATALOG],
        "occupied_count": occupied_count,
        "show_bar": state.snap.show_bar_to_musicians,
    }, to=sid, namespace="/musician")


@sio.on("register", namespace="/musician")
async def m_register(sid, data):
    cookie_sid = (data or {}).get("sid")
    base_id = (data or {}).get("instrument_id")
    if not cookie_sid or not base_id or base_id not in CATALOG_BY_ID:
        await sio.emit("error", {"msg": "registro inválido"}, to=sid, namespace="/musician")
        return
    is_director = (base_id == "director")
    existing_ids = {m.instrument_id for s, m in state.musicians.items() if s != cookie_sid}
    final_id, label = assign_unique_id(base_id, existing_ids)
    sess = register_musician(cookie_sid, final_id, label, base_id_of(final_id), is_director)
    with state.lock:
        sess.socket_id = sid
        # Garante estado limpo (importante tras un reset global no que o cliente
        # mantivo a cookie e se rexistra de novo).
        sess.silenced = False
        sess.is_active = False
        sess.current_loop = None
    await sio.emit("registered", {
        "instrument_id": sess.instrument_id,
        "instrument_label": sess.instrument_label,
        "is_director": sess.is_director,
    }, to=sid, namespace="/musician")
    await to_admin("admin:update", {"musician_count": len(state.musicians)})


@sio.on("disconnect", namespace="/musician")
async def m_disconnect(sid):
    # Localizar sid de socket -> cookie_sid
    cookie_sid = None
    for csid, m in state.musicians.items():
        if m.socket_id == sid:
            cookie_sid = csid; break
    if cookie_sid:
        disconnect(cookie_sid)
    await to_admin("admin:update", {"musician_count": len(state.musicians)})


# ---------- /public ----------------------------------------

@sio.on("connect", namespace="/public")
async def p_connect(sid, environ, auth):
    cookie_sid = (auth or {}).get("sid")
    ip = _client_ip(environ)
    if cookie_sid:
        sess = register_public(cookie_sid)
        with state.lock:
            sess.socket_id = sid
            if ip:
                sess.ip = ip
        await sio.emit("state:restore", public_snapshot(cookie_sid) or {},
                       to=sid, namespace="/public")
    await to_admin("admin:update", {"public_count": len(state.public)})


@sio.on("disconnect", namespace="/public")
async def p_disconnect(sid):
    cookie_sid = None
    for csid, p in state.public.items():
        if p.socket_id == sid:
            cookie_sid = csid; break
    if cookie_sid:
        disconnect(cookie_sid)


@sio.on("vote", namespace="/public")
async def p_vote(sid, data):
    cookie_sid = (data or {}).get("sid")
    loop_id = (data or {}).get("loop_id")
    ok = m4_foliada.cast_vote(cookie_sid, loop_id)
    await sio.emit("vote_ack", {"ok": ok, "loop_id": loop_id}, to=sid, namespace="/public")


@sio.on("shutdown_click", namespace="/public")
async def p_shutdown(sid, data):
    cookie_sid = (data or {}).get("sid")
    ok = await m4_foliada.shutdown_click(cookie_sid)
    await sio.emit("shutdown_ack", {"ok": ok}, to=sid, namespace="/public")


# ---------- /admin -----------------------------------------

@sio.on("connect", namespace="/admin")
async def a_connect(sid, environ, auth):
    snap = state.snap
    await sio.emit("state:snapshot", {
        "movement": snap.movement,
        "midi_status": snap.midi_status,
        "midi_bpm": snap.midi_bpm,
        "midi_connected": snap.midi_connected,
        "dmx_connected": snap.dmx_connected,
        "musician_count": len(state.musicians),
        "public_count": len(state.public),
        "show_bar": snap.show_bar_to_musicians,
        "available_loops": snap.available_loops or list(LOOP_COLORS.keys()),
        "loop_colors": LOOP_COLORS,
        "voting_open": snap.voting_active,
        "shutdown_mode": snap.shutdown_active,
        "previas": m1_video.list_previas(),
    }, to=sid, namespace="/admin")


@sio.on("admin:cmd", namespace="/admin")
async def a_cmd(sid, data):
    cmd = (data or {}).get("cmd")
    args = (data or {}).get("args") or {}
    logger.info(f"ADMIN cmd={cmd} args={args}")

    if cmd == "set_movement":
        mv = int(args.get("movement", 0))
        state.reset_for_new_movement(mv)
        # broadcast a tódolos clientes
        await sio.emit("movement:changed", {"movement": mv}, namespace="/musician")
        await sio.emit("movement:changed", {"movement": mv}, namespace="/projection")
        await sio.emit("movement:changed", {"movement": mv}, namespace="/admin")

    elif cmd == "show_bar":
        with state.lock:
            state.snap.show_bar_to_musicians = bool(args.get("on", True))
        await sio.emit("settings:update",
                       {"show_bar": state.snap.show_bar_to_musicians},
                       namespace="/musician")

    # M1
    elif cmd == "m1_image":
        await m1_video.show_image(int(args.get("index", 0)))
    elif cmd == "m1_play_video":
        await m1_video.play_video()
    elif cmd == "m1_stop_video":
        await m1_video.stop_video()
    elif cmd == "m1_clear":
        await m1_video.clear_projection()

    # M2
    elif cmd == "m2_start_group":
        await m2_lorenz.lorenz.start_group(args.get("group", "G1"))
    elif cmd == "m2_blackout":
        await m2_lorenz.lorenz.blackout()

    # M3
    elif cmd == "m3_start":
        await m3_markov.start()
    elif cmd == "m3_stop":
        await m3_markov.stop()
    elif cmd == "m3_control":
        await m3_markov.control(args)

    # M4
    elif cmd == "m4_open_voting":
        await m4_foliada.open_voting(int(args.get("seconds", 30)))
    elif cmd == "m4_close_voting":
        await m4_foliada.close_voting()
    elif cmd == "m4_start_shutdown":
        await m4_foliada.start_shutdown_mode()

    # Color override
    elif cmd == "color_apply":
        await color_engine.apply(int(args.get("r",0)), int(args.get("g",0)), int(args.get("b",0)),
                                 int(args.get("w",0)),
                                 args.get("effect","static"), float(args.get("speed",1.0)))
    elif cmd == "color_clear":
        await color_engine.clear()

    elif cmd == "global_reset":
        await _global_reset()

    elif cmd == "list_clients":
        # Devolve unha listaxe completa de músicos e público ao admin que pediu.
        with state.lock:
            musicians = [{
                "sid": m.sid,
                "instrument_id": m.instrument_id,
                "instrument_label": m.instrument_label,
                "is_director": m.is_director,
                "silenced": m.silenced,
                "connected": m.socket_id is not None,
                "ip": m.ip or "—",
            } for m in state.musicians.values()]
            public = [{
                "sid": p.sid,
                "connected": p.socket_id is not None,
                "silenced_someone": p.silenced_someone,
                "ip": p.ip or "—",
            } for p in state.public.values()]
        await sio.emit("admin:clients", {
            "musicians": musicians,
            "public": public,
        }, to=sid, namespace="/admin")

    elif cmd == "unassign_musician":
        # Borra a sesión dun músico e mandalle reset:all (con flag para que
        # borre cookie no cliente -> obrigado a re-encher selector).
        target_sid = args.get("sid")
        if target_sid and target_sid in state.musicians:
            ms = state.musicians[target_sid]
            target_socket = ms.socket_id
            label = ms.instrument_label
            with state.lock:
                del state.musicians[target_sid]
            if target_socket:
                await sio.emit("reset:all", {"clear_cookie": True},
                               to=target_socket, namespace="/musician")
            await to_admin("admin:update", {"musician_count": len(state.musicians)})
            logger.info(f"ADMIN unassigned músico={label} sid={target_sid}")

    elif cmd == "test_dmx":
        # Acende todos os LEDs en branco 1.5s e logo apaga
        from ..hardware.dmx_controller import dmx as _dmx
        with _dmx._lock:
            _dmx.universe.set_all(255, 255, 255, 255)
        import asyncio as _aio
        async def _restore():
            await _aio.sleep(1.5)
            with _dmx._lock:
                _dmx.universe.blackout()
        _aio.create_task(_restore())

    else:
        logger.warning(f"ADMIN cmd descoñecido: {cmd}")


# ---------- /projection ------------------------------------

@sio.on("connect", namespace="/projection")
async def proj_connect(sid, environ, auth):
    snap = state.snap
    await sio.emit("state:snapshot", {
        "movement": snap.movement,
        "active_groups": snap.lorenz_active_groups,
        "active_instruments": list(snap.lorenz_active_instruments),
        "last_loop": snap.current_loop,
        "shutdown_mode": snap.shutdown_active,
    }, to=sid, namespace="/projection")


# ---------- Reset global -----------------------------------

async def _global_reset():
    """Limpa o estado: borra músicos, público, votos, apaga DMX/movements,
    e ordena a todos os clientes que volvan á pantalla inicial.

    Reset "de verdade": estado novo coma se a aplicación acabase de arrincar.
    Os clientes reciben `reset:all` cun flag `clear_cookie:true` para que
    o JS borre tamén a cookie de sesión -> será obrigado encher de novo
    a enquisa de selección.
    """
    logger.info("ADMIN cmd=global_reset")
    # Para movements en curso
    for fn in (m2_lorenz.lorenz.blackout, m3_markov.stop, m4_foliada.close_voting,
               m1_video.clear_projection):
        try:
            await fn()
        except Exception as e:
            logger.warning(f"global_reset: {fn.__name__} fallou: {e}")

    # Cancela tarefas internas de m4 (shutdown / voting auto-close)
    try:
        from ..movements import m4_foliada as _m4
        for attr in ("_voting_task", "_shutdown_task"):
            t = getattr(_m4, attr, None)
            if t and not t.done():
                t.cancel()
    except Exception:
        pass

    # DMX off
    try:
        from ..hardware.dmx_controller import dmx as _dmx
        with _dmx._lock:
            _dmx.universe.blackout()
    except Exception:
        pass

    # Reset state -- borrado completo, valores por defecto
    with state.lock:
        state.musicians.clear()
        state.public.clear()
        state.votes_current_round.clear()
        # Snap a valores iniciais de StateSnapshot
        snap = state.snap
        snap.movement = 0
        snap.color_override = None
        # M2
        snap.lorenz_active_group = None
        snap.lorenz_active_groups.clear()
        snap.lorenz_active_instruments.clear()
        snap.lorenz_state = {"x": 0.1, "y": 0.0, "z": 0.0}
        # M3
        snap.markov_running = False
        snap.markov_params.clear()
        # M4 -- volve a ter os 10 loops dispoñibles
        snap.available_loops = list(LOOPS.keys())
        snap.voting_active = False
        snap.voting_loop_choices.clear()
        snap.voting_ends_at = 0.0
        snap.voting_round = 0
        snap.votes_by_voter.clear()
        snap.current_loop = None
        snap.shutdown_active = False
        snap.shutdown_started_at = 0.0

    # Avisa a tódolos clientes para que se reseteen TAMÉN a cookie
    payload = {"clear_cookie": True}
    await sio.emit("reset:all", payload, namespace="/musician")
    await sio.emit("reset:all", payload, namespace="/public")
    await sio.emit("reset:all", payload, namespace="/projection")
    await to_admin("admin:update", {
        "musician_count": 0, "public_count": 0, "counts": {},
        "available_loops": list(LOOPS.keys()),
    })
