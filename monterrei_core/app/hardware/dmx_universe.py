"""Buffer DMX e helpers RGBW."""
from __future__ import annotations
from ..config import settings


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
