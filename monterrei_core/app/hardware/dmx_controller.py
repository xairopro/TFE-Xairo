"""Controlador DMX para Enttec USB Pro vía pyserial.

Soporta dous modos de hardware:
  - Dous adaptadores Enttec USB PRO independentes (un por universo).
    Detéctanse automaticamente. Pódese forzar con dmx_port_hint e dmx_port_hint_2.
  - Un Enttec USB PRO Mk2 (un único porto serie, dous universos con labels diferentes).
    Actívase con MONTERREI_DMX_MK2=true no .env.

Thread propio que envía frames a dmx_fps Hz.
Se non hai dispositivo, queda en modo "stub" loggeando.

Protocolo DMX-USB-Pro:
  0x7E  label  len_LSB  len_MSB  [start_code(0x00) + 512 ch]  0xE7
  Label 6   → saída universo 1 (estándar para todos os modelos)
  Label 202 → saída universo 2 (só Mk2)
"""
from __future__ import annotations
import threading
import time

from ..config import settings
from ..logger import logger
from ..state import state
from .dmx_universe import DualUniverse


class DmxController:
    START        = 0x7E
    END          = 0xE7
    LABEL_OUT_1  = 6    # universo 1 (todos os modelos)
    LABEL_OUT_2  = 202  # universo 2 (só Mk2)

    def __init__(self):
        self.universe = DualUniverse(channels_per_led=settings.dmx_channels_per_led)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._serial1 = None
        self._serial2 = None    # só en modo dous-portos
        self._lock = threading.Lock()
        self._notfound_logged = False

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="dmx")
        self._thread.start()

    def stop(self):
        self._stop.set()

    # ------------------------------------------------------------------ #

    def _find_enttec_ports(self) -> list[str]:
        """Devolve lista de dispositivos Enttec/DMX candidatos."""
        try:
            from serial.tools import list_ports  # type: ignore
        except Exception:
            return []
        hint1 = settings.dmx_port_hint.lower()
        hint2 = settings.dmx_port_hint_2.lower()
        found: list[tuple[int, str]] = []
        for p in list_ports.comports():
            desc = (p.description or "").lower()
            dev  = (p.device or "").lower()
            is_enttec = ("enttec" in desc or "dmx" in desc
                         or "usbserial" in dev or "usbmodem" in dev)
            if not is_enttec and not (hint1 and (hint1 in desc or hint1 in dev)) \
                               and not (hint2 and (hint2 in desc or hint2 in dev)):
                continue
            # Prioridade: hint1=0, hint2=1, o resto=2
            prio = 2
            if hint1 and (hint1 in desc or hint1 in dev): prio = 0
            elif hint2 and (hint2 in desc or hint2 in dev): prio = 1
            found.append((prio, p.device))
        found.sort(key=lambda x: x[0])
        return [d for _, d in found]

    def _open_serial(self, device: str):
        try:
            import serial  # type: ignore
            s = serial.Serial(device, baudrate=57600, timeout=0)
            logger.info(f"DMX: aberto {device}")
            return s
        except Exception as e:
            logger.warning(f"DMX: erro abrindo {device}: {e}")
            return None

    def _try_open(self):
        """Tenta abrir porto(s) segundo o modo configurado.

        Retorna (ser1, ser2) onde ser2 pode ser None.
        """
        try:
            import serial  # type: ignore  # noqa: F401
        except Exception as e:
            logger.warning(f"pyserial non dispoñible: {e}. DMX desactivado.")
            return None, None

        ports = self._find_enttec_ports()

        if settings.dmx_mk2:
            # Un único porto Mk2 — ambos universos polo mesmo serial
            dev = ports[0] if ports else None
            if not dev:
                if not self._notfound_logged:
                    logger.info(f"DMX Mk2: dispositivo non atopado. Modo stub.")
                    self._notfound_logged = True
                return None, None
            self._notfound_logged = False
            ser = self._open_serial(dev)
            return ser, None   # ser2=None → modo Mk2 (mesmo porto para label 202)
        else:
            # Dous portos independentes
            if not ports:
                if not self._notfound_logged:
                    logger.info(f"DMX: ningún dispositivo atopado. Modo stub.")
                    self._notfound_logged = True
                return None, None
            self._notfound_logged = False
            ser1 = self._open_serial(ports[0])
            ser2 = self._open_serial(ports[1]) if len(ports) > 1 else None
            if ser2 is None:
                logger.info("DMX: só 1 porto atopado; o universo 2 non se enviará.")
            return ser1, ser2

    def _send_frame(self, ser, label: int, payload: bytes):
        n = len(payload)
        msg = bytearray()
        msg.append(self.START)
        msg.append(label)
        msg.append(n & 0xFF)
        msg.append((n >> 8) & 0xFF)
        msg.extend(payload)
        msg.append(self.END)
        ser.write(msg)

    def _run(self):
        period = 1.0 / max(1, settings.dmx_fps)
        while not self._stop.is_set():
            self._serial1, self._serial2 = self._try_open()
            with state.lock:
                state.snap.dmx_connected = self._serial1 is not None
            if self._serial1 is None:
                time.sleep(2.0)
                continue
            try:
                while not self._stop.is_set():
                    with self._lock:
                        frame1 = self.universe.u1.frame()
                        frame2 = self.universe.u2.frame()

                    # Universo 1
                    self._send_frame(self._serial1, self.LABEL_OUT_1, frame1)

                    # Universo 2: ou polo segundo porto (2 adaptadores) ou Mk2 label 202
                    if settings.dmx_mk2:
                        self._send_frame(self._serial1, self.LABEL_OUT_2, frame2)
                    elif self._serial2:
                        self._send_frame(self._serial2, self.LABEL_OUT_1, frame2)

                    time.sleep(period)
            except Exception as e:
                logger.warning(f"DMX runtime error: {e}. Reconectando...")
                for s in filter(None, [self._serial1, self._serial2]):
                    try: s.close()
                    except Exception: pass
                self._serial1 = self._serial2 = None
                with state.lock:
                    state.snap.dmx_connected = False
                time.sleep(2.0)


dmx = DmxController()
