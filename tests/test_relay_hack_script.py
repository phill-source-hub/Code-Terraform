"""Adapter test: run the real contract script against the fake game."""

import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "contracts" / "relay_hack.py"
LIBS = Path(__file__).resolve().parent.parent / "scripts" / "libs"


def _contract_game(secret: list[int], probes: list[list[int]], sent: list[tuple]):
    """Fake game whose lock opens for `secret`. Records probes and transmissions."""

    def intercept(code):
        probes.append(list(code))
        return [guess == target for guess, target in zip(code, secret, strict=True)]

    def connect(planet):
        return SimpleNamespace(status="ok", message="connected")

    def transmit(key, value):
        sent.append((key, value))
        return SimpleNamespace(status="correct", message="contract complete")

    game = FakeGame()
    game.components["transmitter"] = FakeComponent(
        id="transmitter",
        type_id="transmitter",
        methods={"connect": connect, "transmit": transmit},
    )
    owner = SimpleNamespace(
        contract=SimpleNamespace(
            id="relay_hack",
            lock=SimpleNamespace(tumblers=6, range=100, intercept=intercept),
        )
    )
    return game, owner


def _run(game, owner, monkeypatch):
    monkeypatch.syspath_prepend(str(LIBS))
    source = SCRIPT.read_text(encoding="utf-8")
    run_script(source, game, filename=str(SCRIPT), extra_globals={"self": owner})


def test_transmits_the_full_code_under_the_contract_id(monkeypatch):
    secret = [7, 42, 0, 99, 13, 58]
    probes: list[list[int]] = []
    sent: list[tuple] = []
    game, owner = _contract_game(secret, probes, sent)
    _run(game, owner, monkeypatch)
    assert sent == [("relay_hack", secret)]
    assert game.printed == ["correct contract complete\n"]


def test_transmits_nothing_when_the_search_fails(monkeypatch):
    probes: list[list[int]] = []
    sent: list[tuple] = []
    game, owner = _contract_game([0, 0, 0, 0, 0, 0], probes, sent)
    owner.contract.lock.intercept = lambda code: [False] * 6
    _run(game, owner, monkeypatch)
    assert sent == []
    assert game.printed[0].startswith("relay_hack failed:")


@pytest.mark.parametrize("seed", range(10))
def test_contract_solver_finds_secret_on_random_secrets(seed, monkeypatch):
    rng = random.Random(seed)
    secret = [rng.randrange(100) for _ in range(6)]
    probes: list[list[int]] = []
    sent: list[tuple] = []
    game, owner = _contract_game(secret, probes, sent)
    _run(game, owner, monkeypatch)
    assert sent == [("relay_hack", secret)]
    assert len(probes) <= 100
