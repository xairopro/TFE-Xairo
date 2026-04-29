"""Simulador de carga: 70 "teléfonos" conectados á Monterrei Core.

Cada cliente:
  1. Pide a páxina de músicos (HTTP GET) para recoller a cookie de sesión.
  2. Conecta vía Socket.IO ao namespace /musician con esa cookie como `sid`.
  3. Recibe o catálogo, escolle un instrumento e envía 'register'.
  4. Mantén a conexión aberta (igual que un teléfono real durante o concerto)
     escoitando eventos `musician:play`, `midi:bar`, etc.

Tamén lanza un puñado de "públicos" (configurables) que conectan a /public
e botan votos cando se abre a votación.

Uso:
    python simulate_70.py                          # 70 músicos a 127.0.0.1:8000
    python simulate_70.py --musicians 70 --public 30 \
        --host 192.168.0.2 --port-musician 8000 --port-public 8001

Requisitos: pip install -r requirements.txt
"""
from __future__ import annotations
import argparse
import asyncio
import logging
import random
import sys
from collections import Counter

import aiohttp
import socketio


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("stress")
# socketio é moi verboso; calámolo
logging.getLogger("socketio").setLevel(logging.WARNING)
logging.getLogger("engineio").setLevel(logging.WARNING)

# Flags globais; actívanse en main() según args
VERBOSE = False        # imprime musician:play, director, voting...
VERBOSE_BARS = False   # imprime midi:bar (moi ruído)


COOKIE_NAME = "monterrei_sid"


class FakePhone:
    """Simula un teléfono dun músico."""

    def __init__(self, idx: int, host: str, port: int, instrument_id: str | None = None):
        self.idx = idx
        self.host = host
        self.port = port
        self.preferred_instrument = instrument_id
        self.sid: str | None = None
        self.assigned_instrument: str | None = None
        self.assigned_label: str | None = None
        self.sio: socketio.AsyncClient | None = None
        self.catalog_event = asyncio.Event()
        self.catalog_data: dict | None = None
        self.registered_event = asyncio.Event()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def fetch_session_cookie(self) -> None:
        async with aiohttp.ClientSession() as http:
            async with http.get(self.base_url + "/", allow_redirects=False) as resp:
                resp.raise_for_status()
                cookies = resp.cookies
                if COOKIE_NAME in cookies:
                    self.sid = cookies[COOKIE_NAME].value
                else:
                    # Fallback: xeramos un sid local
                    import secrets as _s
                    self.sid = _s.token_urlsafe(16)

    async def connect(self) -> None:
        self.sio = socketio.AsyncClient(reconnection=False, logger=False, engineio_logger=False)

        @self.sio.on("catalog", namespace="/musician")
        def _on_catalog(data):
            self.catalog_data = data
            self.catalog_event.set()

        @self.sio.on("registered", namespace="/musician")
        def _on_registered(data):
            self.assigned_instrument = data.get("instrument_id")
            self.assigned_label = data.get("instrument_label")
            self.registered_event.set()

        @self.sio.on("error", namespace="/musician")
        def _on_error(data):
            log.warning("phone#%03d error: %s", self.idx, data)

        # Eventos de "actuación" en tempo real -- imprimimos para que o usuario
        # vexa que efectivamente o servidor lle está falando a este teléfono.
        @self.sio.on("musician:play", namespace="/musician")
        def _on_play(data):
            VERBOSE and log.info("phone#%03d [%s] PLAY  color=%s suffix=%s flash=%s",
                                  self.idx, self.assigned_label or '?',
                                  data.get('color'), data.get('label_suffix'), data.get('flash'))

        @self.sio.on("director:update", namespace="/musician")
        def _on_director(data):
            VERBOSE and log.info("phone#%03d [%s] DIRECTOR event=%s",
                                  self.idx, self.assigned_label or '?', data.get('event'))

        @self.sio.on("midi:bar", namespace="/musician")
        def _on_bar(data):
            # Demasiado verbose para sempre; só cando MIDI realmente avanza
            if VERBOSE_BARS:
                log.info("phone#%03d [%s] BAR %s/T%s",
                         self.idx, self.assigned_label or '?', data.get('bar'), data.get('beat'))

        @self.sio.on("movement:changed", namespace="/musician")
        def _on_mov(data):
            VERBOSE and log.info("phone#%03d [%s] MOVEMENT -> %s",
                                  self.idx, self.assigned_label or '?', data.get('movement'))

        @self.sio.on("reset:all", namespace="/musician")
        def _on_reset(data):
            log.info("phone#%03d [%s] RESET:ALL clear_cookie=%s",
                     self.idx, self.assigned_label or '?', (data or {}).get('clear_cookie'))

        @self.sio.on("settings:update", namespace="/musician")
        def _on_settings(data):
            VERBOSE and log.info("phone#%03d [%s] SETTINGS %s",
                                  self.idx, self.assigned_label or '?', data)

        await self.sio.connect(
            self.base_url,
            namespaces=["/musician"],
            auth={"sid": self.sid},
            transports=["websocket"],
            wait=True,
        )

    async def register_instrument(self) -> None:
        await asyncio.wait_for(self.catalog_event.wait(), timeout=5.0)
        catalog = (self.catalog_data or {}).get("instruments") or []
        if not catalog:
            raise RuntimeError("Catálogo baleiro")
        # Escollemos: o preferido se cabe, ou aleatorio entre os menos ocupados.
        counts: dict = (self.catalog_data or {}).get("occupied_count") or {}
        if self.preferred_instrument:
            choice = self.preferred_instrument
        else:
            non_director = [i for i in catalog if i["id"] != "director"]
            non_director.sort(key=lambda i: counts.get(i["id"], 0))
            choice = non_director[0]["id"] if non_director else catalog[0]["id"]
        await self.sio.emit("register", {"sid": self.sid, "instrument_id": choice},
                            namespace="/musician")
        await asyncio.wait_for(self.registered_event.wait(), timeout=5.0)

    async def stay_alive(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def disconnect(self) -> None:
        if self.sio and self.sio.connected:
            try:
                await self.sio.disconnect()
            except Exception:
                pass


class FakePublic:
    """Simula un teléfono dun asistente do público."""

    def __init__(self, idx: int, host: str, port: int):
        self.idx = idx
        self.host = host
        self.port = port
        self.sid: str | None = None
        self.sio: socketio.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def fetch_session_cookie(self) -> None:
        async with aiohttp.ClientSession() as http:
            async with http.get(self.base_url + "/", allow_redirects=False) as resp:
                resp.raise_for_status()
                if COOKIE_NAME in resp.cookies:
                    self.sid = resp.cookies[COOKIE_NAME].value
                else:
                    import secrets as _s
                    self.sid = _s.token_urlsafe(16)

    async def connect(self) -> None:
        self.sio = socketio.AsyncClient(reconnection=False, logger=False, engineio_logger=False)

        @self.sio.on("m4:voting_open", namespace="/public")
        def _on_voting(data):
            choices = (data or {}).get("choices") or []
            VERBOSE and log.info("public#%03d VOTING_OPEN choices=%s", self.idx, choices)
            if not choices:
                return
            choice = random.choice(choices)
            VERBOSE and log.info("public#%03d   votando -> %s", self.idx, choice)
            asyncio.create_task(self.sio.emit("vote",
                                              {"sid": self.sid, "loop_id": choice},
                                              namespace="/public"))

        @self.sio.on("m4:voting_close", namespace="/public")
        def _on_close(data):
            log.info("public#%03d VOTING_CLOSE winner=%s", self.idx, (data or {}).get('winner'))

        @self.sio.on("m4:shutdown_mode", namespace="/public")
        def _on_sd(data):
            log.info("public#%03d SHUTDOWN_MODE cooldown=%.2fs", self.idx, (data or {}).get('cooldown', 0))

        @self.sio.on("public:update", namespace="/public")
        def _on_upd(data):
            VERBOSE and log.info("public#%03d UPDATE %s", self.idx, data)

        @self.sio.on("reset:all", namespace="/public")
        def _on_reset(data):
            log.info("public#%03d RESET:ALL", self.idx)

        await self.sio.connect(
            self.base_url,
            namespaces=["/public"],
            auth={"sid": self.sid},
            transports=["websocket"],
            wait=True,
        )

    async def stay_alive(self, seconds: float):
        await asyncio.sleep(seconds)

    async def disconnect(self) -> None:
        if self.sio and self.sio.connected:
            try:
                await self.sio.disconnect()
            except Exception:
                pass


async def run_phone(idx: int, host: str, port: int, lifetime: float,
                    stagger: float, results: Counter, assignments: list):
    await asyncio.sleep(stagger)
    phone = FakePhone(idx, host, port)
    try:
        await phone.fetch_session_cookie()
        await phone.connect()
        await phone.register_instrument()
        log.info("phone#%03d ✓ rexistrado como %s", idx, phone.assigned_label or phone.assigned_instrument)
        assignments.append((idx, phone.assigned_label or phone.assigned_instrument))
        results["ok"] += 1
        await phone.stay_alive(lifetime)
    except Exception as e:
        log.error("phone#%03d ✗ %s: %s", idx, type(e).__name__, e)
        results["err"] += 1
    finally:
        await phone.disconnect()


async def run_public(idx: int, host: str, port: int, lifetime: float,
                     stagger: float, results: Counter):
    await asyncio.sleep(stagger)
    pub = FakePublic(idx, host, port)
    try:
        await pub.fetch_session_cookie()
        await pub.connect()
        log.info("public#%03d ✓ conectado", idx)
        results["pub_ok"] += 1
        await pub.stay_alive(lifetime)
    except Exception as e:
        log.error("public#%03d ✗ %s: %s", idx, type(e).__name__, e)
        results["pub_err"] += 1
    finally:
        await pub.disconnect()


async def main():
    parser = argparse.ArgumentParser(description="Simulador de 70 teléfonos para Monterrei Core.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port-musician", type=int, default=8000)
    parser.add_argument("--port-public", type=int, default=8001)
    parser.add_argument("--musicians", type=int, default=70)
    parser.add_argument("--public", type=int, default=0,
                        help="Número de asistentes do público a simular (0 = só músicos)")
    parser.add_argument("--lifetime", type=float, default=120.0,
                        help="Segundos que cada conexión permanece aberta")
    parser.add_argument("--stagger", type=float, default=0.05,
                        help="Atraso (s) entre lanzamentos sucesivos para non saturar de golpe")
    parser.add_argument("--verbose", action="store_true",
                        help="Imprime cada evento que recibe cada teléfono")
    parser.add_argument("--verbose-bars", action="store_true",
                        help="Imprime tamén midi:bar (moi ruído)")
    args = parser.parse_args()

    global VERBOSE, VERBOSE_BARS
    VERBOSE = args.verbose
    VERBOSE_BARS = args.verbose_bars

    log.info("== Monterrei Stress Test ==")
    log.info("Músicos: %d -> http://%s:%d", args.musicians, args.host, args.port_musician)
    if args.public:
        log.info("Público: %d -> http://%s:%d", args.public, args.host, args.port_public)
    log.info("Vida útil de cada conexión: %.1fs (Ctrl-C para abortar)", args.lifetime)

    results: Counter = Counter()
    assignments: list = []   # (idx, instrument_label) por orde de asignación
    tasks = []
    for i in range(args.musicians):
        tasks.append(asyncio.create_task(
            run_phone(i + 1, args.host, args.port_musician,
                      args.lifetime, i * args.stagger, results, assignments)))
    for i in range(args.public):
        tasks.append(asyncio.create_task(
            run_public(i + 1, args.host, args.port_public,
                       args.lifetime, i * args.stagger, results)))

    # Pequena pausa para que se rexistren os músicos antes de imprimir resumo
    async def _print_summary_when_ready():
        # Agarda ata que tódolos músicos teñan asignación (ou pasen 8s)
        for _ in range(80):
            if len(assignments) >= args.musicians:
                break
            await asyncio.sleep(0.1)
        log.info("== Instrumentos asignados ==")
        for idx, lbl in sorted(assignments):
            log.info("  phone#%03d -> %s", idx, lbl)
        log.info("============================")
    tasks.append(asyncio.create_task(_print_summary_when_ready()))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        log.warning("Cancelado polo usuario")

    log.info("== Resultado ==")
    log.info("Músicos OK:  %d", results.get("ok", 0))
    log.info("Músicos KO:  %d", results.get("err", 0))
    log.info("Público OK:  %d", results.get("pub_ok", 0))
    log.info("Público KO:  %d", results.get("pub_err", 0))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
