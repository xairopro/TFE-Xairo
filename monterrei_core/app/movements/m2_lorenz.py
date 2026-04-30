"""Movemento 2: Lorenz + activación incremental de músicos.

Cada grupo (G1, G2, G3) lánzao o admin manualmente. Os grupos son acumulativos
(non se desactivan ao pasar ao seguinte). O botón Blackout silencia todo.

Algoritmo:
- Estado de Lorenz (x,y,z) con σ=10, ρ=28, β=8/3.
- Punto inicial aleatorio.
- Proxección 2D: usamos (x, z) normalizado a [-1,1] para mapear á topografía.
- En cada tick (60 fps) intégrase RK4 simplificado (Euler dt=0.005). Cando a
  proxección cae preto dunha cela dun músico do grupo activo aínda non
  activado, actívase.
- Garantía 40s: se ao chegar ao tempo límite quedan músicos sen activar,
  fórzanse de un en un en intervalos rápidos ata completar.
- Cada activación envía cambio á proxección (frecha+puntos), aos músicos
  involucrados (pantalla verde / cor do grupo) e ao DMX.
"""
from __future__ import annotations
import asyncio
import math
import random
import time

from ..core.broadcaster import to_projection, to_musicians_by_base, to_admin, to_directors, to_all_musicians
from ..state import state
from ..data.groups import GROUPS, GROUP_COLOR_HEX, GROUP_RGBW
from ..data.topography import POSITIONS, closest_instrument
from ..data.led_layout import led_for_instrument
from ..hardware.dmx_controller import dmx
from ..logger import logger


SIGMA, RHO, BETA = 10.0, 28.0, 8.0 / 3.0
DT = 0.004
TARGET_SECONDS = 40.0
SMOOTH_ALPHA = 0.12
ACTIVATION_RADIUS2 = 0.02
MIN_ACTIVATION_INTERVAL = 0.85
START_GRACE_SECONDS = 2.0
FORCE_INTERVAL_SECONDS = 1.0


class LorenzEngine:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.current_group: str | None = None
        self.x, self.y, self.z = 0.1, 0.0, 0.0
        self._activated_in_group: set[str] = set()
        self._start_time: float = 0.0
        self._next_activation_at: float = 0.0
        self._next_forced_at: float = 0.0
        self._sx: float = 0.0
        self._sy: float = 0.0

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def reset_state(self):
        self.x = random.uniform(-15, 15)
        self.y = random.uniform(-15, 15)
        self.z = random.uniform(5, 35)
        self._sx = 0.0
        self._sy = 0.0

    async def start_group(self, group: str):
        if group not in GROUPS:
            return
        if self.is_running():
            self._stop.set()
            try: await self._task
            except Exception: pass
        self._stop.clear()
        self.reset_state()
        self.current_group = group
        with state.lock:
            state.snap.lorenz_active_group = group
            if group not in state.snap.lorenz_active_groups:
                state.snap.lorenz_active_groups.append(group)
        self._activated_in_group = set()
        self._start_time = time.monotonic()
        self._next_activation_at = self._start_time + START_GRACE_SECONDS
        self._next_forced_at = self._start_time + TARGET_SECONDS

        await to_projection("m2:group_started", {"group": group, "color": GROUP_COLOR_HEX[group]})
        await to_directors("director:update", {"group": group, "event": "group_started"})
        await to_admin("m2:progress", {
            "group": group,
            "active": 0,
            "total": len(GROUPS[group]),
            "running": True,
        })
        self._task = asyncio.create_task(self._run())

    async def blackout(self):
        if self._task:
            self._stop.set()
            try: await self._task
            except Exception: pass
        with state.lock:
            state.snap.lorenz_active_group = None
            state.snap.lorenz_active_groups.clear()
            state.snap.lorenz_active_instruments.clear()
            for m in state.musicians.values():
                m.is_active = False
        # DMX: blackout
        with dmx._lock:
            dmx.universe.blackout()
        await to_all_musicians("musician:play", {"playing": False, "color": "#000", "flash": False})
        await to_projection("m2:blackout", {})
        await to_directors("director:update", {"event": "blackout"})
        await to_admin("m2:progress", {"group": None, "active": 0, "total": 0, "running": False})

    async def _run(self):
        group = self.current_group
        if not group:
            return
        targets_total = set(GROUPS[group])
        # Ignora os instrumentos que xa estaban activos por grupos anteriores
        with state.lock:
            already_on = set(state.snap.lorenz_active_instruments)
        targets = targets_total - already_on
        tick_period = 1.0 / 60.0
        force_after = TARGET_SECONDS * 0.82

        try:
            while not self._stop.is_set() and len(self._activated_in_group) < len(targets):
                # RK4-like (Euler simple bastante suave a dt=0.005)
                dx = SIGMA * (self.y - self.x)
                dy = self.x * (RHO - self.z) - self.y
                dz = self.x * self.y - BETA * self.z
                self.x += DT * dx
                self.y += DT * dy
                self.z += DT * dz

                # Abrimos máis a cobertura e suavizamos para evitar saltos bruscos.
                raw_px = max(-1, min(1, self.x / 18.0))
                raw_py = max(-1, min(1, (self.z - 24.0) / 18.0))
                self._sx += SMOOTH_ALPHA * (raw_px - self._sx)
                self._sy += SMOOTH_ALPHA * (raw_py - self._sy)
                px, py = self._sx, self._sy

                with state.lock:
                    state.snap.lorenz_state = {"x": self.x, "y": self.y, "z": self.z, "px": px, "py": py}

                # Procura cela máis próxima entre os pendentes
                pending = targets - self._activated_in_group
                now = time.monotonic()
                if now >= self._next_activation_at:
                    hit = closest_instrument(px, py, only_in=pending)
                    if hit is not None:
                        pos = POSITIONS.get(hit)
                        if pos and (px - pos[0])**2 + (py - pos[1])**2 < ACTIVATION_RADIUS2:
                            await self._activate(hit)
                            self._next_activation_at = now + MIN_ACTIVATION_INTERVAL

                # Forza activación se imos atrasados
                elapsed = time.monotonic() - self._start_time
                if elapsed > force_after and pending and now >= self._next_forced_at:
                    await self._activate(next(iter(pending)))
                    self._next_forced_at = now + FORCE_INTERVAL_SECONDS

                await to_projection("m2:tick", {
                    "px": px, "py": py, "x": self.x, "y": self.y, "z": self.z,
                    "active": sorted(state.snap.lorenz_active_instruments),
                })
                await asyncio.sleep(tick_period)
        except asyncio.CancelledError:
            pass

    async def _activate(self, base_id: str):
        if base_id in self._activated_in_group:
            return
        self._activated_in_group.add(base_id)
        with state.lock:
            state.snap.lorenz_active_instruments.add(base_id)
            for m in state.musicians.values():
                if m.base_instrument_id == base_id and not m.is_director:
                    m.is_active = True

        color = GROUP_COLOR_HEX[self.current_group or "G1"]
        await to_musicians_by_base({base_id}, "musician:play", {
            "playing": True, "color": color, "flash": True,
            "label_suffix": "TOCA",
        })
        await to_projection("m2:activated", {"instrument": base_id, "color": color})
        await to_directors("director:update", {"event": "instrument_activated",
                                                "instrument": base_id, "group": self.current_group})

        # DMX: enciende o LED máis próximo (proporcional aos músicos vivos)
        led = led_for_instrument(base_id)
        if led is not None:
            r, g, b, w = GROUP_RGBW[self.current_group or "G1"]
            with dmx._lock:
                dmx.universe.set_led(led, r, g, b, w)

        # Admin: progress X/Y do grupo actual
        group = self.current_group or "G1"
        await to_admin("m2:progress", {
            "group": group,
            "active": len(self._activated_in_group),
            "total": len(GROUPS.get(group, [])),
            "running": True,
        })


lorenz = LorenzEngine()
