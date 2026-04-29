"""Controlador DMX para Enttec USB Pro vía pyserial.

- Thread propio enviando frames a `dmx_fps` Hz.
- Se non hai dispositivo, queda en modo "stub" loggeando.
- Protocolo DMX-USB-Pro: cabeceira 0x7E, label 6 (Output), len LSB+MSB, payload (start code 0x00 + 512 ch), trailing 0xE7.
"""
from __future__ import annotations
import threading
import time

from ..config import settings
from ..logger import logger
from ..state import state
from .dmx_universe import DmxUniverse


class DmxController:
    LABEL_OUTPUT = 6
    START = 0x7E
    END = 0xE7

    def __init__(self):
        self.universe = DmxUniverse()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._serial = None
        self._lock = threading.Lock()
        self._notfound_logged = False

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="dmx")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _try_open(self):
        try:
            import serial  # type: ignore
            from serial.tools import list_ports  # type: ignore
        except Exception as e:
            logger.warning(f"pyserial non dispoñible: {e}. DMX desactivado.")
            return None

        ports = list(list_ports.comports())
        hint = settings.dmx_port_hint.lower()
        candidate = None
        for p in ports:
            desc = (p.description or "").lower()
            dev = (p.device or "").lower()
            if hint and (hint in desc or hint in dev):
                candidate = p.device; break
            if "enttec" in desc or "dmx" in desc or "usbserial" in dev or "usbmodem" in dev:
                candidate = p.device; break
        if not candidate:
            if not self._notfound_logged:
                logger.info(f"DMX: dispositivo non atopado. Portos: {[p.device for p in ports]}. Modo stub.")
                self._notfound_logged = True
            return None
        self._notfound_logged = False
        try:
            ser = serial.Serial(candidate, baudrate=57600, timeout=0)
            logger.info(f"DMX: aberto {candidate}")
            return ser
        except Exception as e:
            logger.warning(f"DMX: erro abrindo {candidate}: {e}")
            return None

    def _send_frame(self, ser, payload: bytes):
        n = len(payload)
        msg = bytearray()
        msg.append(self.START)
        msg.append(self.LABEL_OUTPUT)
        msg.append(n & 0xFF)
        msg.append((n >> 8) & 0xFF)
        msg.extend(payload)
        msg.append(self.END)
        ser.write(msg)

    def _run(self):
        period = 1.0 / max(1, settings.dmx_fps)
        while not self._stop.is_set():
            self._serial = self._try_open()
            with state.lock:
                state.snap.dmx_connected = self._serial is not None
            if self._serial is None:
                # Sen hardware: seguir vivo enviando "frames virtuais" sen bloquear o resto.
                time.sleep(2.0)
                continue
            try:
                while not self._stop.is_set():
                    with self._lock:
                        frame = self.universe.frame()
                    self._send_frame(self._serial, frame)
                    time.sleep(period)
            except Exception as e:
                logger.warning(f"DMX runtime error: {e}. Reconectando...")
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None
                with state.lock:
                    state.snap.dmx_connected = False
                time.sleep(2.0)


dmx = DmxController()
