"""Estado global da aplicación.

Centralízao todo nunha clase singleton thread-safe (RLock). Compartido
entre threads (MIDI/DMX) e o event loop (sockets/movements).
"""
from __future__ import annotations
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MusicianSession:
    sid: str                         # session id (cookie)
    instrument_id: str               # ex: "cl3-1", "vc", "director"
    instrument_label: str            # texto humano: "Clarinete 3 - 1"
    base_instrument_id: str          # para Lorenz (sen sufixo): "cl3", "vc"
    is_director: bool = False
    is_active: bool = False          # actualmente "tocando"
    current_loop: str | None = None  # M4
    socket_id: str | None = None
    last_seen: float = 0.0
    silenced: bool = False           # apagado en Crisis
    ip: str = ""                     # IP do cliente (informativo no admin)


@dataclass
class PublicSession:
    sid: str
    socket_id: str | None = None
    last_seen: float = 0.0
    last_vote: str | None = None
    silenced_someone: bool = False
    next_shutdown_allowed: float = 0.0
    ip: str = ""


@dataclass
class Vote:
    voter_sid: str
    loop_id: str
    timestamp: float


@dataclass
class StateSnapshot:
    movement: int = 0                          # 0 = repouso, 1..4
    midi_status: str = "stopped"               # stopped | playing
    midi_bpm: float = 0.0
    midi_bar_real: int = 0                     # nº de compás dende o start MIDI
    midi_bar_display: int = 0                  # mapeado segundo o score
    midi_beat: int = 0                         # 1 ou 2 en 6/8 (pulso composto)
    midi_pass: int = 0                         # 0=clickin, 1=primeiro pase, 2+=pases sen repeticións
    show_bar_to_musicians: bool = True
    dmx_connected: bool = False
    midi_connected: bool = False
    # M2
    lorenz_active_group: str | None = None     # "G1" | "G2" | "G3" | None
    lorenz_active_groups: list[str] = field(default_factory=list)  # acumulativos
    lorenz_active_instruments: set[str] = field(default_factory=set)  # base_ids
    lorenz_state: dict = field(default_factory=lambda: {"x": 0.1, "y": 0.0, "z": 0.0})
    # M3
    markov_running: bool = False
    markov_params: dict = field(default_factory=dict)
    # M4
    available_loops: list[str] = field(default_factory=list)
    voting_active: bool = False
    voting_loop_choices: list[str] = field(default_factory=list)
    voting_ends_at: float = 0.0
    voting_round: int = 0
    votes_by_voter: dict = field(default_factory=dict)   # public_sid -> loop_id
    current_loop: str | None = None
    shutdown_active: bool = False
    shutdown_started_at: float = 0.0
    shutdown_progressive_at: float = 0.0
    shutdown_cooldown: float = 1.0
    # Color override (admin)
    color_override: dict | None = None         # {"r":..,"g":..,"b":..,"w":..,"effect":"static|pulse|wave|strobe","speed":..}


class StateManager:
    """Singleton de estado. Acceder via `state`."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.snap = StateSnapshot()
        self.musicians: dict[str, MusicianSession] = {}  # sid -> sess
        self.public: dict[str, PublicSession] = {}
        self.votes_current_round: list[Vote] = []
        # Listeners (callbacks). Permiten desacoplar mutacións de broadcasts.
        self._listeners: list[Any] = []

    # --- contexto thread-safe ----------------------------------
    @property
    def lock(self):
        return self._lock

    # --- listeners --------------------------------------------
    def on_change(self, cb):
        self._listeners.append(cb)

    def emit_change(self, event: str, payload: dict | None = None):
        for cb in self._listeners:
            try:
                cb(event, payload or {})
            except Exception:  # noqa
                pass

    # --- helpers ------------------------------------------------
    def musicians_alive(self) -> list[MusicianSession]:
        return [m for m in self.musicians.values() if not m.silenced and not m.is_director]

    def public_alive(self) -> list[PublicSession]:
        return [p for p in self.public.values()]

    def directors(self) -> list[MusicianSession]:
        return [m for m in self.musicians.values() if m.is_director]

    def reset_for_new_movement(self, movement: int):
        with self._lock:
            self.snap.movement = movement
            self.snap.color_override = None
            for m in self.musicians.values():
                m.is_active = False
                m.current_loop = None


state = StateManager()
