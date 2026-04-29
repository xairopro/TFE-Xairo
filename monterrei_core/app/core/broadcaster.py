"""Helpers de broadcast por rol/grupo/loop sobre Socket.IO."""
from __future__ import annotations
from .socket_server import sio
from ..state import state


async def to_admin(event: str, data: dict | None = None):
    await sio.emit(event, data or {}, namespace="/admin")


async def to_projection(event: str, data: dict | None = None):
    await sio.emit(event, data or {}, namespace="/projection")


async def to_public(event: str, data: dict | None = None):
    await sio.emit(event, data or {}, namespace="/public")


async def to_all_musicians(event: str, data: dict | None = None):
    await sio.emit(event, data or {}, namespace="/musician")


async def to_musician(sid_socket: str, event: str, data: dict | None = None):
    await sio.emit(event, data or {}, to=sid_socket, namespace="/musician")


async def to_directors(event: str, data: dict | None = None):
    """Envía a todos os músicos marcados como director."""
    for m in state.directors():
        if m.socket_id:
            await sio.emit(event, data or {}, to=m.socket_id, namespace="/musician")


async def to_musicians_by_base(base_ids: set[str], event: str, data: dict | None = None):
    """Envía só aos músicos cuxo instrumento base estea no set."""
    for m in state.musicians.values():
        if m.base_instrument_id in base_ids and not m.is_director and m.socket_id:
            await sio.emit(event, data or {}, to=m.socket_id, namespace="/musician")


async def broadcast_all(event: str, data: dict | None = None):
    for ns in ("/admin", "/musician", "/public", "/projection"):
        await sio.emit(event, data or {}, namespace=ns)
