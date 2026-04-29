"""Tests do mapeado de compás (M2)."""
from app.data.score_map import real_bar_to_display, BarPos


def test_clickin():
    for i in range(1, 9):
        p = real_bar_to_display(i)
        assert p.in_clickin, f"bar {i} debería ser claqueta"
        assert p.pass_number == 0


def test_first_pass_starts_at_bar_1():
    p = real_bar_to_display(9)
    assert p.in_clickin is False
    assert p.pass_number == 1
    assert p.display_bar == 1


def test_first_pass_repetition():
    # Compás 9 (real_bar 9+8=17) é o último da repetición -> debe ser display 8
    p = real_bar_to_display(9 + 8 + 7 - 1)  # ...
    assert p.pass_number == 1


def test_second_pass_skips_first_endings():
    # Avanza ata o pase 2
    # Pase1 ten len = 1+8+7+9+7+9+7+17 = 65 compases
    # primeiro compás do pase 2 = real_bar 9 + 65 = 74
    p = real_bar_to_display(74)
    assert p.pass_number == 2
    assert p.display_bar == 2  # comeza saltando o 1


def test_second_pass_skips_9():
    # No pase 2, despois do display 8 vai ao 10 (sálta 9)
    # primeiros 7 elementos: 2..8 -> 8º elemento (index 7) é o 10
    p = real_bar_to_display(74 + 7)
    assert p.pass_number == 2
    assert p.display_bar == 10
