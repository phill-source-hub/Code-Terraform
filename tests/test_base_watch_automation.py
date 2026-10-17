"""Adapter tests: the base_watch Automation against a fake power_control, machines and bus."""

import ast
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_comms import FakeSignalBus
from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "automations" / "base_watch.py"


class _Stop(Exception):
    """Ends the Automation's endless loop after the requested number of passes."""


class PassCountingGame(FakeGame):
    def __init__(self, passes: int):
        super().__init__()
        self.passes_left = passes

    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        self.passes_left -= 1
        if self.passes_left <= 0:
            raise _Stop


def grid(net=50.0, stored=400.0, capacity=500.0):
    return SimpleNamespace(net=net, stored=stored, capacity=capacity)


def run(grids=None, bus=None, deployed=("harvester_1", "scanner_1"), power=True, passes=1):
    game = PassCountingGame(passes)
    if power:
        game.components["power_control"] = FakeComponent(
            id="power_control",
            type_id="power_control",
            methods={"grids": lambda: [] if grids is None else grids},
        )
    for slot in deployed:
        game.components[slot] = FakeComponent(id=slot, type_id="machine", methods={})
    if bus is not None:
        game.components["comms"] = bus.as_component()
    # No `self` is passed: an Automation has no machine (manual, Automations).
    with suppress(_Stop):
        run_script(SCRIPT.read_text(encoding="utf-8"), game, filename=str(SCRIPT))
    return game


def fresh_bus(**ages):
    """A bus where each named slot has a heartbeat `age` seconds old (None means no heartbeat)."""
    bus = FakeSignalBus()
    for slot, age in ages.items():
        if age is None:
            continue
        bus.broadcast("status." + slot, {"heat": 0})
        bus.broadcasts["status." + slot].age_seconds = float(age)
    return bus


def test_a_healthy_base_reports_base_ok():
    game = run(grids=[grid()], bus=fresh_bus(harvester_1=5, scanner_1=5))
    assert game.printed == ["base ok\n"]
    assert game.statuses[-1] == ("base ok", "info")


def test_a_power_deficit_is_a_warning():
    game = run(grids=[grid(net=-12.4)], bus=fresh_bus(harvester_1=5, scanner_1=5))
    assert "warning: power deficit: net -12 W\n" in game.printed
    assert game.statuses[-1][1] == "warn"


def test_a_low_battery_is_a_warning():
    game = run(grids=[grid(net=5.0, stored=50.0, capacity=500.0)], bus=fresh_bus(harvester_1=5))
    assert "warning: low battery: 10% stored\n" in game.printed


def test_a_silent_machine_is_reported_with_its_age():
    game = run(grids=[grid()], bus=fresh_bus(harvester_1=200, scanner_1=5))
    assert "warning: harvester_1: silent for 200 s\n" in game.printed


def test_a_deployed_machine_that_never_reported_is_reported():
    game = run(grids=[grid()], bus=fresh_bus(harvester_1=5, scanner_1=None))
    assert "warning: scanner_1: no heartbeat yet\n" in game.printed


def test_a_slot_with_no_machine_is_not_watched():
    game = run(grids=[grid()], bus=fresh_bus(harvester_1=5), deployed=("harvester_1",))
    assert not any("scanner_1" in line for line in game.printed)


def test_the_alert_list_is_broadcast_on_the_bus():
    bus = fresh_bus(harvester_1=5, scanner_1=5)
    run(grids=[grid(net=-1.0)], bus=bus)
    assert bus.latest("base.alerts") == ["power deficit: net -1 W"]


def test_a_repeated_state_is_printed_once():
    game = run(grids=[grid(net=-1.0)], bus=fresh_bus(harvester_1=5), passes=3)
    assert game.printed.count("warning: power deficit: net -1 W\n") == 1


def test_a_missing_power_control_is_an_alert_not_a_crash():
    game = run(power=False, bus=fresh_bus(harvester_1=5, scanner_1=5))
    assert "warning: power_control not found\n" in game.printed


def test_without_the_signal_bus_power_is_still_watched():
    game = run(grids=[grid(net=-3.0)])
    assert "warning: power deficit: net -3 W\n" in game.printed


def test_the_automation_never_uses_self():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "self" not in names
