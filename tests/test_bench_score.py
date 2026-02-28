from __future__ import annotations

from sentinelqa.bench import score


def test_compute_prf_perfect_match():
    expected = ["a", "b"]
    produced = ["a", "b"]
    res = score.compute_prf(expected, produced)
    assert res["f1"] == 1.0
    assert res["tp"] == 2 and res["fp"] == 0 and res["fn"] == 0


def test_compute_prf_partial():
    expected = ["a", "b"]
    produced = ["a", "c"]
    res = score.compute_prf(expected, produced)
    assert res["tp"] == 1
    assert res["fp"] == 1
    assert res["fn"] == 1
    assert res["f1"] == 0.5
