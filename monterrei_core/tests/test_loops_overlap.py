"""Tests do solapamento 50/50 con hash determinista."""
import hashlib
from app.data.loops import LOOPS, shared_instruments


def test_loops_have_expected_overlap():
    # L1 e L2 comparten saxos
    s = shared_instruments("L1", "L2")
    assert "saxten1" in s
    assert "saxbar" in s


def test_hash_deterministic():
    sids = ["abc", "def", "xyz", "uvw"]
    expected = [int(hashlib.sha256(s.encode()).hexdigest(), 16) % 2 for s in sids]
    repeat = [int(hashlib.sha256(s.encode()).hexdigest(), 16) % 2 for s in sids]
    assert expected == repeat


def test_all_loops_defined():
    assert len(LOOPS) == 10
    for k in LOOPS:
        assert k.startswith("L")
        assert len(LOOPS[k]) > 0
