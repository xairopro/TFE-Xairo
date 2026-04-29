"""Color override do admin (estático/pulso/onda/estrobo).
Lánzase como tarefa asyncio mentras está activo. Aplícase ao DMX.
"""
from __future__ import annotations
import asyncio
import math
import time

from ..hardware.dmx_controller import dmx
from ..state import state


class ColorEngine:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def apply(self, r: int, g: int, b: int, w: int = 0,
                    effect: str = "static", speed: float = 1.0):
        if self._task and not self._task.done():
            self._stop.set()
            try: await self._task
            except Exception: pass
        self._stop.clear()
        with state.lock:
            state.snap.color_override = {"r": r, "g": g, "b": b, "w": w,
                                          "effect": effect, "speed": speed}
        self._task = asyncio.create_task(self._run(r, g, b, w, effect, speed))

    async def clear(self):
        if self._task:
            self._stop.set()
            try: await self._task
            except Exception: pass
        with state.lock:
            state.snap.color_override = None

    async def _run(self, r, g, b, w, effect: str, speed: float):
        led_count = dmx.universe.led_count
        try:
            t0 = time.monotonic()
            while not self._stop.is_set():
                t = (time.monotonic() - t0) * max(0.1, speed)
                if effect == "static":
                    with dmx._lock:
                        dmx.universe.set_all(r, g, b, w)
                    await asyncio.sleep(0.1)
                elif effect == "pulse":
                    k = 0.5 + 0.5 * math.sin(t * 2 * math.pi)
                    with dmx._lock:
                        dmx.universe.set_all(int(r*k), int(g*k), int(b*k), int(w*k))
                    await asyncio.sleep(1/30)
                elif effect == "wave":
                    with dmx._lock:
                        for i in range(led_count):
                            phase = (i / led_count) * 2 * math.pi
                            k = 0.5 + 0.5 * math.sin(t * 2 * math.pi + phase)
                            dmx.universe.set_led(i, int(r*k), int(g*k), int(b*k), int(w*k))
                    await asyncio.sleep(1/30)
                elif effect == "strobe":
                    on = int((t * 8) % 2) == 0
                    with dmx._lock:
                        if on: dmx.universe.set_all(r, g, b, w)
                        else: dmx.universe.set_all(0, 0, 0, 0)
                    await asyncio.sleep(1/16)
                else:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass


color_engine = ColorEngine()
