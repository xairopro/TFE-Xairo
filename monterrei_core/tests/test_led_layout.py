"""Test do mapeado físico LED-músico."""
from app.data.led_layout import LED_ANGLES, LED_COUNT, led_for_instrument, section_for_loop


def test_led_count():
    assert len(LED_ANGLES) == LED_COUNT


def test_led_for_known_instrument():
    led = led_for_instrument("trp1")
    assert led is None or 0 <= led < LED_COUNT


def test_section_for_loop_distinct():
    s1 = set(section_for_loop(1))
    s2 = set(section_for_loop(2))
    assert s1.isdisjoint(s2)
    assert len(s1) == 6
