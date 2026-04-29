"""Tests da xeración de IDs únicos para músicos duplicados."""
from app.data.instruments import assign_unique_id, base_id_of


def test_first_user_keeps_base_id():
    new_id, label = assign_unique_id("cl3", set())
    assert new_id == "cl3"
    assert label == "Clarinete 3"


def test_second_user_gets_suffix():
    existing = {"cl3"}
    new_id, label = assign_unique_id("cl3", existing)
    assert new_id == "cl3-2"
    assert "Clarinete 3" in label


def test_third_user():
    existing = {"cl3", "cl3-2"}
    new_id, _ = assign_unique_id("cl3", existing)
    assert new_id == "cl3-3"


def test_base_id_of():
    assert base_id_of("cl3") == "cl3"
    assert base_id_of("cl3-2") == "cl3"
    assert base_id_of("vc-15") == "vc"
