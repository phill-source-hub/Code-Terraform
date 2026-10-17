"""Adapter test: run the real machine script against the fake game.

The script loops forever, so the fake `sleep` raises `_Stop` to end each run.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "harvester_1.py"
LIBS = Path(__file__).resolve().parent.parent / "scripts" / "libs"


class _Stop(Exception):
    """Raised by the fake sleep to end the script's while-loop after a set number of polls."""


class StoppingGame(FakeGame):
    def __init__(self, polls: int, **kwargs):
        super().__init__(**kwargs)
        self.polls_left = polls

    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        self.polls_left -= 1
        if self.polls_left <= 0:
            raise _Stop


def _grid(net, stored, capacity):
    return SimpleNamespace(net=net, stored=stored, capacity=capacity)


def _game_with_grids(grid_snapshots, polls):
    game = StoppingGame(polls=polls)
    game.components["power_control"] = FakeComponent(
        id="power_control",
        type_id="power_control",
        methods={"grids": lambda: grid_snapshots},
    )
    return game


@pytest.fixture
def script_source(monkeypatch):
    # The script does `from power_status import ...`, so the Library folder must be importable.
    monkeypatch.syspath_prepend(str(LIBS))
    return SCRIPT.read_text(encoding="utf-8")


def test_healthy_grid_prints_ok_and_sets_info_status(script_source):
    game = _game_with_grids([_grid(net=20.0, stored=400.0, capacity=500.0)], polls=2)
    with pytest.raises(_Stop):
        run_script(script_source, game, filename=str(SCRIPT))
    assert game.printed == ["power ok\n"]
    assert game.warnings == []
    assert game.statuses[-1] == ("power ok", "info")


def test_deficit_warns_and_sets_warn_status(script_source):
    game = _game_with_grids([_grid(net=-30.0, stored=400.0, capacity=500.0)], polls=1)
    with pytest.raises(_Stop):
        run_script(script_source, game, filename=str(SCRIPT))
    assert game.warnings == ["power deficit: net -30 W\n"]
    assert game.statuses[-1] == ("power deficit: net -30 W", "warn")


def test_unchanged_message_is_not_repeated(script_source):
    game = _game_with_grids([_grid(net=20.0, stored=400.0, capacity=500.0)], polls=5)
    with pytest.raises(_Stop):
        run_script(script_source, game, filename=str(SCRIPT))
    assert game.printed == ["power ok\n"]
    assert len(game.statuses) == 5


def test_missing_power_control_reports_error_and_exits(script_source):
    game = StoppingGame(polls=1)
    run_script(script_source, game, filename=str(SCRIPT))
    assert game.statuses == [("power_control not found", "error")]
    assert game.printed == []
