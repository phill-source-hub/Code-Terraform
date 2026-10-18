"""Adapter tests: rover_1 and charging_station_1 against fakes of the rover and the station.

The scripts loop forever. Each test ends the loop by raising _Stop from the first sleep it reaches,
so the test sees exactly what the script did before it waited.
"""

import sys
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

ROOT = Path(__file__).resolve().parent.parent
ROVER = ROOT / "scripts" / "main" / "rover_1.py"
STATION = ROOT / "scripts" / "main" / "charging_station_1.py"
sys.path.insert(0, str(ROOT / "scripts" / "libs"))


class _Stop(Exception):
    """Ends a script's loop at its first sleep."""


def _ok(**extra):
    return SimpleNamespace(status="ok", message="", **extra)


def _slot(index, slot_type, module_id):
    return SimpleNamespace(index=index, type=slot_type, module_id=module_id)


def _stop_at_first_sleep(game):
    def sleep(seconds, /):
        raise _Stop

    game.sleep = sleep


def test_rover_swaps_in_highest_drill_tier_from_base_inventory():
    game = FakeGame()
    _stop_at_first_sleep(game)
    game.components["notebook"] = FakeComponent(
        "notebook", "notebook", {"has": lambda key: True, "set": lambda k, v: _ok()}
    )
    game.components["inventory"] = FakeComponent(
        "inventory",
        "inventory",
        {"count": lambda item: 1 if item == "drill_module_heavy" else 0},
    )
    game.components["journal"] = FakeComponent(
        "journal", "journal", {"surveyed_sites": lambda planet: []}
    )
    calls = []
    slots = [
        _slot(0, "nav", "nav_module"),
        _slot(1, "sonar_basic", "sonar_module"),
        _slot(2, "drill_basic", "drill_module"),
    ]
    rover = SimpleNamespace(
        nav=SimpleNamespace(
            get_position=lambda: SimpleNamespace(x=0.0, y=0.0),
            get_distance_to=lambda x, y: 0.0,
            set_target=lambda x, y: _ok(),
            set_throttle=lambda p: _ok(),
            brake=lambda: _ok(),
        ),
        battery=SimpleNamespace(level=lambda: 1.0, wh=lambda: 100.0),
        cargo=SimpleNamespace(count=lambda: 0, stacks=lambda: []),
        output=SimpleNamespace(connect=lambda n: _ok(), send=lambda i, c: _ok()),
        modules=lambda: slots,
        unmount=lambda index: (calls.append(("unmount", index)), _ok())[1],
        mount=lambda index, item: (calls.append(("mount", index, item)), _ok())[1],
    )

    with suppress(_Stop):
        run_script(ROVER.read_text(encoding="utf-8"), game, str(ROVER), {"self": rover})

    assert calls == [("unmount", 2), ("mount", 2, "drill_module_heavy")]


def test_rover_keeps_current_drill_when_nothing_better_is_owned():
    game = FakeGame()
    _stop_at_first_sleep(game)
    game.components["notebook"] = FakeComponent("notebook", "notebook", {"has": lambda key: True})
    game.components["inventory"] = FakeComponent(
        "inventory", "inventory", {"count": lambda item: 0}
    )
    game.components["journal"] = FakeComponent(
        "journal", "journal", {"surveyed_sites": lambda planet: []}
    )
    calls = []
    rover = SimpleNamespace(
        nav=SimpleNamespace(
            get_position=lambda: SimpleNamespace(x=0.0, y=0.0),
            get_distance_to=lambda x, y: 0.0,
            set_target=lambda x, y: _ok(),
            set_throttle=lambda p: _ok(),
            brake=lambda: _ok(),
        ),
        battery=SimpleNamespace(level=lambda: 1.0, wh=lambda: 100.0),
        cargo=SimpleNamespace(count=lambda: 0, stacks=lambda: []),
        output=SimpleNamespace(connect=lambda n: _ok(), send=lambda i, c: _ok()),
        modules=lambda: [_slot(2, "drill_basic", "drill_module")],
        unmount=lambda index: (calls.append(("unmount", index)), _ok())[1],
        mount=lambda index, item: (calls.append(("mount", index, item)), _ok())[1],
    )

    with suppress(_Stop):
        run_script(ROVER.read_text(encoding="utf-8"), game, str(ROVER), {"self": rover})

    assert calls == []


def test_charge_station_queues_docked_vehicle_once_and_skips_busy_ones():
    game = FakeGame()
    _stop_at_first_sleep(game)
    charged = []
    states = {"rover_1": {"state": "docked"}, "rover_2": {"state": "charging"}}

    def charge(vehicle_id, target):
        charged.append((vehicle_id, target))
        return _ok()

    station = SimpleNamespace(
        get_docked=lambda: ["rover_1", "rover_2"],
        status=lambda vehicle_id: states[vehicle_id],
        charge=charge,
    )

    with suppress(_Stop):
        run_script(STATION.read_text(encoding="utf-8"), game, str(STATION), {"self": station})

    assert charged == [("rover_1", 1.0)]


def test_charge_station_warns_when_queue_refuses_a_vehicle():
    game = FakeGame()
    _stop_at_first_sleep(game)
    station = SimpleNamespace(
        get_docked=lambda: ["rover_1"],
        status=lambda vehicle_id: {"state": "docked"},
        charge=lambda vehicle_id, target: SimpleNamespace(
            status="station_offline", message="offline"
        ),
    )

    with suppress(_Stop):
        run_script(STATION.read_text(encoding="utf-8"), game, str(STATION), {"self": station})

    assert game.statuses == [("charge rover_1 station_offline: offline", "warn")]
