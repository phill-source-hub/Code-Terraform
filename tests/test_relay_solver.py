import random

import pytest

from scripts.libs.relay_solver import solve


def _lock(secret: list[int], calls: list[list[int]]):
    """Fake RelayLock.intercept that records every probe it receives."""

    def intercept(code: list[int]) -> list[bool]:
        calls.append(list(code))
        return [guess == target for guess, target in zip(code, secret, strict=True)]

    return intercept


def test_solves_known_secret():
    calls: list[list[int]] = []
    secret = [7, 42, 0, 99, 13, 58]
    assert solve(_lock(secret, calls), tumblers=6, value_range=100) == secret


@pytest.mark.parametrize("seed", range(20))
def test_solves_random_secrets(seed):
    rng = random.Random(seed)
    secret = [rng.randrange(100) for _ in range(6)]
    assert solve(_lock(secret, []), tumblers=6, value_range=100) == secret


def test_never_needs_more_than_range_probes():
    calls: list[list[int]] = []
    secret = [99, 99, 99, 99, 99, 99]  # worst case: the last candidate
    solve(_lock(secret, calls), tumblers=6, value_range=100)
    assert len(calls) == 100


def test_stops_early_once_every_tumbler_is_known():
    calls: list[list[int]] = []
    solve(_lock([0, 0, 0, 0, 0, 0], calls), tumblers=6, value_range=100)
    assert len(calls) == 1


def test_each_probe_sets_all_tumblers_to_one_candidate():
    calls: list[list[int]] = []
    solve(_lock([5, 9, 1, 2, 3, 4], calls), tumblers=6, value_range=100)
    assert all(len(set(call)) == 1 for call in calls)


def test_raises_when_a_tumbler_is_never_true():
    # Probe that never reports True: a tumbler with no correct value in range.
    with pytest.raises(RuntimeError, match="no correct value"):
        solve(lambda code: [False] * 6, tumblers=6, value_range=10)


def test_raises_when_probe_returns_wrong_shape():
    with pytest.raises(ValueError, match="expected 6 results"):
        solve(lambda code: [False] * 5, tumblers=6, value_range=10)
