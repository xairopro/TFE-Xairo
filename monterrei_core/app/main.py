"""Entrypoint ASGI. Lanza Uvicorn en dous portos (main + public) co mesmo
servidor Socket.IO compartido.
"""
from __future__ import annotations
import asyncio
import signal

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import socketio
import uvicorn

from .config import settings, BASE_DIR
from .logger import logger
from .core.socket_server import sio
from .core import handlers  # noqa: F401  (rexistra os handlers)
from .routes import make_main_router, make_admin_router, make_public_router
from .hardware.midi_clock import midi_clock
from .hardware.dmx_controller import dmx
from .core.broadcaster import broadcast_all


async def _emit_async(event: str, data: dict):
    # Usado polo MIDI thread cando precisa empuxar a sockets
    await broadcast_all(event, data)


def build_main_app() -> FastAPI:
    app = FastAPI(title="Monterrei Core – musicians")
    app.include_router(make_main_router())
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    return app


def build_admin_app() -> FastAPI:
    app = FastAPI(title="Monterrei Core – admin")
    app.include_router(make_admin_router())
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    return app


def build_public_app() -> FastAPI:
    app = FastAPI(title="Monterrei Core – public")
    app.include_router(make_public_router())
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    return app


def wrap_with_sio(fastapi_app: FastAPI):
    """Devolve unha ASGIApp que combina FastAPI + Socket.IO."""
    return socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


async def main():
    midi_clock.on_event = _emit_async
    midi_clock.start(asyncio.get_event_loop())
    dmx.start()

    main_app = wrap_with_sio(build_main_app())
    admin_app = wrap_with_sio(build_admin_app())
    public_app = wrap_with_sio(build_public_app())

    configs = [
        *(uvicorn.Config(main_app, host=host, port=settings.port_main,
                         log_level=settings.log_level.lower(), lifespan="off")
          for host in settings.main_bind_hosts),
        uvicorn.Config(admin_app, host=settings.host, port=settings.port_admin,
                       log_level=settings.log_level.lower(), lifespan="off"),
        uvicorn.Config(public_app, host=settings.host, port=settings.port_public,
                       log_level=settings.log_level.lower(), lifespan="off"),
    ]
    if settings.bind_port_80:
        configs.append(uvicorn.Config(public_app, host=settings.host, port=settings.port_public_low,
                                      log_level=settings.log_level.lower(), lifespan="off"))

    servers = [uvicorn.Server(c) for c in configs]

    logger.info(
        f"Monterrei Core arrincando en host_main={settings.main_bind_hosts} host_shared={settings.host}"
    )
    for c in configs:
        logger.info(f"  Host {c.host} porto {c.port}")

    # Manexador de SIGINT/SIGTERM
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, stop_event.set)
        except NotImplementedError:
            pass

    server_tasks = [asyncio.create_task(s.serve()) for s in servers]
    await stop_event.wait()
    logger.info("Sinal de parada recibido. Cerrando servidores...")
    for s in servers:
        s.should_exit = True
    for t in server_tasks:
        try: await t
        except Exception: pass
    midi_clock.stop()
    dmx.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
