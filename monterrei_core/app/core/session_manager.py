"""Xestor de sesións por cookie. Permite restaurar estado tras recarga."""
from __future__ import annotations
import secrets
import time
from typing import Optional
from fastapi import Request, Response

from ..config import settings
from ..state import state, MusicianSession, PublicSession


def get_or_create_sid(request: Request, response: Response) -> str:
    """Le ou crea unha cookie de sesión persistente."""
    sid = request.cookies.get(settings.session_cookie)
    if not sid:
        sid = secrets.token_urlsafe(16)
        response.set_cookie(
            key=settings.session_cookie,
            value=sid,
            max_age=60 * 60 * 8,   # 8h, suficiente para o concerto
            httponly=False,         # JS precisa lelo para socket.io auth
            samesite="lax",
        )
    return sid


def musician_snapshot(sid: str) -> dict | None:
    sess = state.musicians.get(sid)
    if not sess:
        return None
    return {
        "sid": sess.sid,
        "instrument_id": sess.instrument_id,
        "instrument_label": sess.instrument_label,
        "is_director": sess.is_director,
        "is_active": sess.is_active,
        "current_loop": sess.current_loop,
        "silenced": sess.silenced,
    }


def public_snapshot(sid: str) -> dict | None:
    sess = state.public.get(sid)
    if not sess:
        return None
    return {
        "sid": sess.sid,
        "voting_open": state.snap.voting_active,
        "voting_choices": state.snap.voting_loop_choices,
        "voting_ends_at": state.snap.voting_ends_at,
        "shutdown_mode": state.snap.shutdown_active,
        "next_shutdown_allowed": sess.next_shutdown_allowed,
    }


def register_musician(sid: str, instrument_id: str, instrument_label: str,
                      base_instrument_id: str, is_director: bool = False) -> MusicianSession:
    with state.lock:
        sess = state.musicians.get(sid)
        if sess is None:
            sess = MusicianSession(
                sid=sid,
                instrument_id=instrument_id,
                instrument_label=instrument_label,
                base_instrument_id=base_instrument_id,
                is_director=is_director,
                last_seen=time.time(),
            )
            state.musicians[sid] = sess
        else:
            sess.instrument_id = instrument_id
            sess.instrument_label = instrument_label
            sess.base_instrument_id = base_instrument_id
            sess.is_director = is_director
            sess.last_seen = time.time()
        return sess


def register_public(sid: str) -> PublicSession:
    with state.lock:
        sess = state.public.get(sid)
        if sess is None:
            sess = PublicSession(sid=sid, last_seen=time.time())
            state.public[sid] = sess
        else:
            sess.last_seen = time.time()
        return sess


def disconnect(sid: str):
    """Non eliminamos a sesión (resiliencia ante reload), só anulamos socket."""
    with state.lock:
        if sid in state.musicians:
            state.musicians[sid].socket_id = None
        if sid in state.public:
            state.public[sid].socket_id = None
