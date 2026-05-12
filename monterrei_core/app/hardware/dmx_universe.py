"""Buffer DMX e helpers RGBW.

Layout físico (2 universos, 5 focos × 6 LEDs × 4ch RGBW = 120 ch por universo):

  Universo 1 (DMX1):
    Foco 1  → LEDs  0– 5  → ch   1– 24
    Foco 2  → LEDs  6–11  → ch  25– 48
    Foco 3  → LEDs 12–17  → ch  49– 72
    Foco 4  → LEDs 18–23  → ch  73– 96
    Foco 5  → LEDs 24–29  → ch  97–120

  Universo 2 (DMX2):
    Foco 6  → LEDs 30–35  → ch   1– 24
    Foco 7  → LEDs 36–41  → ch  25– 48
    Foco 8  → LEDs 42–47  → ch  49– 72
    Foco 9  → LEDs 48–53  → ch  73– 96
    Foco 10 → LEDs 54–59  → ch  97–120
"""
from __future__ import annotations
from ..config import settings

# LEDs por universo físico (5 focos × 6 LEDs)
LEDS_PER_UNIVERSE = 30


class DmxUniverse:
    """Universo DMX de 512 canles. Soporta LEDs RGBW continuos a partir de canle 1."""

    def __init__(self, led_count: int | None = None, channels_per_led: int | None = None):
        self.led_count = led_count or settings.dmx_led_count
        self.channels_per_led = channels_per_led or settings.dmx_channels_per_led
        self.data = bytearray(513)  # canle 0 = start code (0x00)
        self.dirty = True

    def set_led(self, index: int, r: int, g: int, b: int, w: int = 0):
        if not (0 <= index < self.led_count):
            return
        base = 1 + index * self.channels_per_led
        self.data[base + 0] = max(0, min(255, r))
        self.data[base + 1] = max(0, min(255, g))
        self.data[base + 2] = max(0, min(255, b))
        if self.channels_per_led >= 4:
            self.data[base + 3] = max(0, min(255, w))
        self.dirty = True

    def set_all(self, r: int, g: int, b: int, w: int = 0):
        for i in range(self.led_count):
            self.set_led(i, r, g, b, w)

    def fade_all(self, factor: float):
        """Multiplica todas as intensidades RGBW por factor in [0,1]."""
        last = 1 + self.led_count * self.channels_per_led
        for i in range(1, last):
            self.data[i] = int(self.data[i] * factor)
        self.dirty = True

    def blackout(self):
        last = 1 + self.led_count * self.channels_per_led
        for i in range(1, last):
            self.data[i] = 0
        self.dirty = True

    def frame(self) -> bytes:
        return bytes(self.data)


class DualUniverse:
    """Presenta a mesma API que DmxUniverse pero xestiona dous universos físicos.

    LEDs 0–29  → Universe 1 (DMX1, Focos 1–5)
    LEDs 30–59 → Universe 2 (DMX2, Focos 6–10)

    Todo o código existente que usa dmx.universe.set_led(índice, r, g, b, w)
    segue funcionando sen cambios: o índice global (0–59) distribúese
    automaticamente ao universo correcto.
    """

    def __init__(self, channels_per_led: int | None = None):
        cpl = channels_per_led or settings.dmx_channels_per_led
        self.u1 = DmxUniverse(led_count=LEDS_PER_UNIVERSE, channels_per_led=cpl)
        self.u2 = DmxUniverse(led_count=LEDS_PER_UNIVERSE, channels_per_led=cpl)
        self.led_count = LEDS_PER_UNIVERSE * 2   # 60
        self.channels_per_led = cpl

    def _dispatch(self, index: int) -> tuple[DmxUniverse, int]:
        """Devolve (universo, índice_local) para un índice global."""
        if index < LEDS_PER_UNIVERSE:
            return self.u1, index
        return self.u2, index - LEDS_PER_UNIVERSE

    def set_led(self, index: int, r: int, g: int, b: int, w: int = 0):
        u, li = self._dispatch(index)
        u.set_led(li, r, g, b, w)

    def set_all(self, r: int, g: int, b: int, w: int = 0):
        self.u1.set_all(r, g, b, w)
        self.u2.set_all(r, g, b, w)

    def fade_all(self, factor: float):
        self.u1.fade_all(factor)
        self.u2.fade_all(factor)

    def blackout(self):
        self.u1.blackout()
        self.u2.blackout()

    def snapshot(self) -> list[dict]:
        """Devolve estado RGBW dos 60 LEDs para o monitor externo."""
        result = []
        for u_idx, (u, offset) in enumerate([(self.u1, 0), (self.u2, LEDS_PER_UNIVERSE)], start=1):
            for i in range(LEDS_PER_UNIVERSE):
                base = 1 + i * self.channels_per_led
                fixture = (offset + i) // 6       # foco 0–9
                led_in_fixture = (offset + i) % 6
                result.append({
                    "led":            offset + i,
                    "universe":       u_idx,
                    "fixture":        fixture,
                    "fixture_label":  f"Foco {fixture + 1}",
                    "led_in_fixture": led_in_fixture,
                    "dmx_channel":    base,         # canal dentro do seu universo
                    "r": u.data[base],
                    "g": u.data[base + 1],
                    "b": u.data[base + 2],
                    "w": u.data[base + 3] if self.channels_per_led >= 4 else 0,
                })
        return result
