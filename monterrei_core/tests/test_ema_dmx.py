"""Test do EMA + protocolo DMX."""
from app.utils.ema import EMA
from app.hardware.dmx_universe import DmxUniverse


def test_ema_initializes_with_first_value():
    e = EMA(0.15)
    assert e.update(120) == 120


def test_ema_smooths():
    e = EMA(0.5)
    e.update(120); e.update(180)
    assert 130 <= e.value <= 170


def test_dmx_universe_set_led():
    u = DmxUniverse(led_count=10, channels_per_led=4)
    u.set_led(0, 255, 128, 0, 64)
    assert u.data[1] == 255
    assert u.data[2] == 128
    assert u.data[3] == 0
    assert u.data[4] == 64


def test_dmx_blackout():
    u = DmxUniverse(led_count=10, channels_per_led=4)
    u.set_all(255, 255, 255, 255)
    u.blackout()
    assert all(b == 0 for b in u.data[1:41])
