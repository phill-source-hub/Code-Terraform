"""Adapter tests: run the real harvester_1 power monitor against a fake power_control."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.libs.power_status import classify, summarize_grids
from tests.harness.fake_game import FakeComponent, FakeGame, run_script


class _Stop(Exception):
    """Ends the monitor's endless loop after its first sleep."""


class StopOnSleep(FakeGame):
    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        raise _Stop


def run_loop(path, game, owner):
    try:
        run_script(
            path.read_text(encoding="utf-8"),
            game,
            filename=str(path),
            extra_globals={"self": owner},
        )
    except _Stop:
        return


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "harvester_1.py"


def _grid(net, stored, capacity):
    return SimpleNamespace(net=net, stored=stored, capacity=capacity)


def _game(grids):
    game = StopOnSleep()
    game.components["power_control"] = FakeComponent(
        id="power_control",
        type_id="power_control",
        methods={"grids": lambda: grids},
    )
    return game


def _run(grids):
    game = _game(grids)
    run_loop(SCRIPT, game, owner=None)
    return game


def test_healthy_grid_prints_ok_and_sets_info_status():
    game = _run([_grid(net=20.0, stored=400.0, capacity=500.0)])
    assert game.printed == ["power ok\n"]
    assert game.warnings == []
    assert game.statuses[-1] == ("power ok", "info")


def test_deficit_warns_and_sets_warn_status():
    game = _run([_grid(net=-30.0, stored=400.0, capacity=500.0)])
    assert game.warnings == ["power deficit: net -30 W\n"]
    assert game.statuses[-1] == ("power deficit: net -30 W", "warn")


def test_low_battery_warns():
    game = _run([_grid(net=5.0, stored=50.0, capacity=500.0)])
    assert game.warnings == ["low battery: 10% stored\n"]


def test_missing_power_control_reports_error_and_exits():
    game = StopOnSleep()
    run_loop(SCRIPT, game, owner=None)
    assert game.statuses == [("power_control not found", "error")]


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line


@pytest.mark.parametrize(
    "net, stored, capacity",
    [
        (20.0, 400.0, 500.0),
        (-12.4, 400.0, 500.0),
        (5.0, 50.0, 500.0),
        (5.0, 0.0, 0.0),
        (-1.0, 10.0, 500.0),
    ],
)
def test_script_messages_match_library_rules(net, stored, capacity):
    # Parity: the inlined rules report the same alerts as the tested library.
    game = _run([_grid(net=net, stored=stored, capacity=capacity)])
    expected = classify(net, stored, capacity)
    shown = "; ".join(expected) or "power ok"
    assert (game.warnings or game.printed)[-1].strip() == shown
    assert summarize_grids([_grid(net, stored, capacity)])["net"] == net
