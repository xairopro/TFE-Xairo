"""Thread de reloxo MIDI vía IAC. Adaptado do piloto en Logic ↔ Python.

Características:
- Le 0xF8 (clock), 0xFA (start), 0xFC (stop), 0xFB (continue), 0xF2 (songpos).
- BPM = ventá rolante 48 ticks + EMA (α configurable). Filtro [bpm_min, bpm_max].
- Para 6/8 e 24 PPQN -> 72 ticks/compás.
- Aplica `bpm_divider` configurable (corrección se Logic envía dobre/metade).
- Empuxa eventos ao event loop principal vía `loop.call_soon_threadsafe`.
- Reconecta automaticamente se o porto desaparece.
- Se mido non está dispoñible (ex: tests sen IAC), o thread loga e queda inactivo.
"""
from __future__ import annotations
import asyncio
import threading
import time
from typing import Callable

from ..config import settings
from ..logger import logger
from ..state import state
from ..utils.ema import EMA
from ..data.score_map import real_bar_from_pulses, real_bar_to_display, beat_in_bar


PULSES_PER_BAR_6_8 = 72   # 24 PPQN * 6/8 * 2 corcheas-por-tick? -> 24*3 = 72
PULSES_PER_BEAT_COMP = 36  # negra puntillada en 6/8 a 24 PPQN


class MidiClock:
    def __init__(self, on_event: Callable[[str, dict], None] | None = None):
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ema = EMA(alpha=settings.bpm_ema_alpha)
        self._times: list[float] = []
        self._lock = threading.Lock()
        self.on_event = on_event   # Callable(event_name, payload)
        self._port_in = None

    def start(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._thread = threading.Thread(target=self._run, daemon=True, name="midi-clock")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _emit(self, event: str, data: dict):
        if not self._loop or not self.on_event:
            return
        try:
            self._loop.call_soon_threadsafe(lambda: self._loop.create_task(self.on_event(event, data)))
        except Exception as e:  # noqa
            logger.warning(f"MIDI emit error: {e}")

    def _run(self):
        try:
            import mido  # type: ignore
        except Exception as e:
            logger.warning(f"mido non dispoñible: {e}. MIDI desactivado.")
            return

        retry = 5
        while not self._stop.is_set():
            try:
                inputs = mido.get_input_names()
            except Exception as e:
                logger.warning(f"MIDI list error: {e}")
                time.sleep(retry); continue

            port_name = next((p for p in inputs if settings.midi_port_hint.lower() in p.lower()), None)
            if not port_name:
                logger.info(f"MIDI: porto co hint '{settings.midi_port_hint}' non atopado. Retry {retry}s")
                with state.lock:
                    state.snap.midi_connected = False
                self._emit("hw:status", {"midi": False, "ports": inputs})
                time.sleep(retry); continue

            with state.lock:
                state.snap.midi_connected = True
            self._emit("hw:status", {"midi": True, "port": port_name})
            logger.info(f"MIDI: escoitando en '{port_name}'")

            total_pulses = 0
            pulse_count = 0

            try:
                with mido.open_input(port_name) as port:
                    for msg in port:
                        if self._stop.is_set():
                            break
                        t = msg.type
                        if t == "start":
                            with state.lock:
                                state.snap.midi_status = "playing"
                                state.snap.midi_bar_real = 0
                                state.snap.midi_bar_display = 0
                                state.snap.midi_pass = 0
                            with self._lock:
                                self._times.clear()
                                self._ema.reset()
                            total_pulses = 0; pulse_count = 0
                            self._emit("midi:status", {"status": "playing"})
                            logger.info("MIDI ▶ START")

                        elif t == "stop":
                            with state.lock:
                                state.snap.midi_status = "stopped"
                                state.snap.midi_bpm = 0.0
                            with self._lock:
                                self._times.clear()
                                self._ema.reset()
                            self._emit("midi:status", {"status": "stopped"})
                            self._emit("midi:bpm", {"bpm": 0.0})
                            logger.info("MIDI ■ STOP")

                        elif t == "continue":
                            with state.lock:
                                state.snap.midi_status = "playing"
                            self._emit("midi:status", {"status": "playing"})

                        elif t == "clock":
                            now = time.perf_counter()
                            bpm = self._calc_bpm(now)
                            pulse_count += 1
                            total_pulses += 1

                            real_bar = real_bar_from_pulses(total_pulses, PULSES_PER_BAR_6_8)
                            beat = beat_in_bar(total_pulses, PULSES_PER_BAR_6_8)
                            pos = real_bar_to_display(real_bar)

                            with state.lock:
                                state.snap.midi_bpm = bpm
                                state.snap.midi_bar_real = real_bar
                                state.snap.midi_bar_display = pos.display_bar
                                state.snap.midi_pass = pos.pass_number
                                state.snap.midi_beat = beat

                            # Emitimos bpm cada 24 pulsos (1 negra), bar cada 36 (T)
                            if pulse_count % 24 == 0:
                                self._emit("midi:bpm", {"bpm": bpm})
                            if pulse_count % 36 == 0:
                                self._emit("midi:bar", {
                                    "bar": pos.display_bar,
                                    "beat": beat,
                                    "pass": pos.pass_number,
                                    "in_clickin": pos.in_clickin,
                                    "real_bar": real_bar,
                                })
            except Exception as e:
                logger.warning(f"MIDI port error: {e}. Reconectando en {retry}s")
                with state.lock:
                    state.snap.midi_connected = False
                self._emit("hw:status", {"midi": False})
                time.sleep(retry)

    def _calc_bpm(self, now: float) -> float:
        with self._lock:
            self._times.append(now)
            if len(self._times) > 48:
                self._times = self._times[-48:]
            if len(self._times) < 2:
                return 0.0
            intervals = [self._times[i+1] - self._times[i] for i in range(len(self._times)-1)]
            avg = sum(intervals) / len(intervals)
            if avg <= 0:
                return 0.0
            raw = 60.0 / (24.0 * avg)
            raw /= max(0.001, settings.bpm_divider)
            if not (settings.bpm_min <= raw <= settings.bpm_max):
                return 0.0
            return round(self._ema.update(raw), 1)


midi_clock = MidiClock()
