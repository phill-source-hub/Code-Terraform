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


def _nocturna(contacts):
    box = SimpleNamespace(min_x=-1000.0, max_x=1000.0, min_y=-1000.0, max_y=1000.0)
    return FakeComponent(
        "nocturna",
        "planet",
        {
            "points_of_interest": lambda: contacts,
            "get_bounds": lambda: box,
        },
    )


def _contact(x, y, scanned=False):
    return SimpleNamespace(x=x, y=y, scanned=scanned, kind="unknown")


def _world(game, *, inventory=None, contacts=()):
    """Fill the game with the components the rover reads at base, and return the call log."""
    game.components["inventory"] = FakeComponent(
        "inventory", "inventory", {"count": lambda item: (inventory or {}).get(item, 0)}
    )
    game.components["journal"] = FakeComponent(
        "journal",
        "journal",
        {"surveyed_sites": lambda planet: [], "discovered_sites": lambda planet: []},
    )
    game.components["nocturna"] = _nocturna(list(contacts))
    saved = []
    game.components["notebook"] = FakeComponent(
        "notebook",
        "notebook",
        {
            "set": lambda key, value: saved.append((key, value)) or _ok(),
            "has": lambda key: False,
            "get": lambda key, default: default,
        },
    )
    return saved


def _rover(calls, *, modules, scans=None, targets=None):
    """A rover parked at base with a full battery. Movement and actions are logged in `calls`."""
    scans = scans if scans is not None else []
    targets = targets if targets is not None else []

    def scan():
        scans.append(True)
        return SimpleNamespace(status="ok", message="", sites=[])

    return SimpleNamespace(
        nav=SimpleNamespace(
            get_position=lambda: SimpleNamespace(x=0.0, y=0.0),
            get_distance_to=lambda x, y: 0.0,
            set_target=lambda x, y: (targets.append((x, y)), _ok())[1],
            set_throttle=lambda p: _ok(),
            brake=lambda: _ok(),
        ),
        battery=SimpleNamespace(level=lambda: 1.0, wh=lambda: 100.0),
        cargo=SimpleNamespace(count=lambda: 0, stacks=lambda: []),
        output=SimpleNamespace(connect=lambda n: _ok(), send=lambda i, c: _ok()),
        sonar=SimpleNamespace(scan=scan, survey=lambda found: _ok(), range=lambda: 50.0),
        modules=lambda: modules,
        unmount=lambda index: (calls.append(("unmount", index)), _ok())[1],
        mount=lambda index, item: (calls.append(("mount", index, item)), _ok())[1],
        is_being_rescued=lambda: False,
    )


def _run_rover(game, rover):
    with suppress(_Stop):
        run_script(ROVER.read_text(encoding="utf-8"), game, str(ROVER), {"self": rover})


def test_rover_swaps_in_highest_drill_tier_from_base_inventory():
    game = FakeGame()
    _stop_at_first_sleep(game)
    _world(game, inventory={"drill_module_heavy": 1})
    calls = []
    slots = [
        _slot(0, "nav", "nav_module"),
        _slot(1, "sonar_basic", "sonar_module"),
        _slot(2, "drill_basic", "drill_module"),
    ]

    _run_rover(game, _rover(calls, modules=slots))

    assert calls == [("unmount", 2), ("mount", 2, "drill_module_heavy")]


def test_rover_keeps_current_drill_when_nothing_better_is_owned():
    game = FakeGame()
    _stop_at_first_sleep(game)
    _world(game)
    calls = []

    _run_rover(game, _rover(calls, modules=[_slot(2, "drill_basic", "drill_module")]))

    assert calls == []


def test_rover_surveys_nearest_unscanned_contact_then_saves_map():
    game = FakeGame()
    _stop_at_first_sleep(game)
    saved = _world(game, contacts=[_contact(900, 0), _contact(-30, 40), _contact(5, 5, True)])
    targets, scans = [], []
    rover = _rover(
        [], modules=[_slot(2, "drill_basic", "drill_module")], scans=scans, targets=targets
    )

    _run_rover(game, rover)

    assert targets == [(-30, 40)]
    assert scans == [True]
    key, grid_map = saved[-1]
    assert key == "rover.map"
    assert grid_map["base"] == {"x": 0.0, "y": 0.0}
    assert len(grid_map["contacts"]) == 3


def _station(*, docked=(), states=None, charged=None, rescuing=False, dispatch=None):
    """A charging station fake. `dispatch` is the status dispatch_rescue returns (default ok)."""
    states = states or {}
    charged = charged if charged is not None else []
    dispatched = []

    def dispatch_rescue(vehicle_name, target):
        dispatched.append((vehicle_name, target))
        return SimpleNamespace(status=dispatch or "ok", message="refused" if dispatch else "")

    def charge(vehicle_id, target):
        charged.append((vehicle_id, target))
        return _ok()

    station = SimpleNamespace(
        get_docked=lambda: list(docked),
        status=lambda vehicle_id: states.get(vehicle_id, {"state": "docked"}),
        charge=charge,
        is_rescuing=lambda: rescuing,
        dispatch_rescue=dispatch_rescue,
    )
    return station, charged, dispatched


def _stranded_rover(game, status="stranded"):
    game.components["rover_1"] = FakeComponent("rover_1", "rover", {"status": lambda: status})


def _run_station(game, station):
    with suppress(_Stop):
        run_script(STATION.read_text(encoding="utf-8"), game, str(STATION), {"self": station})


def test_charge_station_queues_docked_vehicle_once_and_skips_busy_ones():
    game = FakeGame()
    _stop_at_first_sleep(game)
    _stranded_rover(game, status="idle")
    station, charged, _ = _station(
        docked=["rover_1", "rover_2"],
        states={"rover_1": {"state": "docked"}, "rover_2": {"state": "charging"}},
    )

    _run_station(game, station)

    assert charged == [("rover_1", 1.0)]


def test_charge_station_warns_when_queue_refuses_a_vehicle():
    game = FakeGame()
    _stop_at_first_sleep(game)
    _stranded_rover(game, status="idle")
    station, _, _ = _station(docked=["rover_1"])
    station.charge = lambda vehicle_id, target: SimpleNamespace(
        status="station_offline", message="offline"
    )

    _run_station(game, station)

    assert game.statuses == [("charge rover_1 station_offline: offline", "warn")]


def test_charge_station_sends_drone_to_stranded_rover():
    game = FakeGame()
    _stop_at_first_sleep(game)
    _stranded_rover(game, status="stranded")
    station, _, dispatched = _station()

    _run_station(game, station)

    assert dispatched == [("rover_1", 1.0)]
    assert game.statuses == [("rescue drone sent to rover_1", "info")]


def test_charge_station_does_not_send_second_drone_while_one_is_out():
    game = FakeGame()
    _stop_at_first_sleep(game)
    _stranded_rover(game, status="stranded")
    station, _, dispatched = _station(rescuing=True)

    _run_station(game, station)

    assert dispatched == []


def test_charge_station_leaves_healthy_rover_alone():
    game = FakeGame()
    _stop_at_first_sleep(game)
    _stranded_rover(game, status="moving")
    station, _, dispatched = _station()

    _run_station(game, station)

    assert dispatched == []


def test_charge_station_reports_refused_rescue_once():
    game = FakeGame()
    sleeps = []

    def sleep(seconds, /):
        sleeps.append(seconds)
        if len(sleeps) >= 3:
            raise _Stop

    game.sleep = sleep
    _stranded_rover(game, status="stranded")
    station, _, dispatched = _station(dispatch="station_offline")

    _run_station(game, station)

    assert len(dispatched) == 3
    assert game.statuses == [("rescue rover_1 station_offline: refused", "warn")]


def test_rover_far_from_base_on_low_charge_drives_home_without_error():
    # Low charge away from base sends the rover to recharge first. That path drives home, and it
    # must pass the energy rate along. The rover here can never arrive, so the drive stalls and
    # the script keeps running until the sleep limit stops it.
    game = FakeGame()
    sleeps = []

    def sleep(seconds, /):
        sleeps.append(seconds)
        if len(sleeps) >= 100:
            raise _Stop

    game.sleep = sleep
    _world(game, contacts=[_contact(-30, 40)])
    scans = []
    rover = _rover([], modules=[_slot(2, "drill_basic", "drill_module")], scans=scans)
    rover.nav.get_position = lambda: SimpleNamespace(x=100.0, y=0.0)
    rover.nav.get_distance_to = lambda x, y: ((100.0 - x) ** 2 + (0.0 - y) ** 2) ** 0.5
    rover.battery = SimpleNamespace(level=lambda: 0.03, wh=lambda: 3.0)

    _run_rover(game, rover)

    assert scans == []
    assert len(sleeps) >= 100


def test_rover_places_base_and_scanned_contact_markers():
    game = FakeGame()
    _stop_at_first_sleep(game)
    placed = []
    contact = _contact(-30, 40)
    _world(game, contacts=[contact])
    game.components["markers"] = FakeComponent(
        "markers", "markers", {"place": lambda *args: (placed.append(args), _ok())[1]}
    )
    rover = _rover([], modules=[_slot(2, "drill_basic", "drill_module")])

    def scan():
        contact.scanned = True
        contact.kind = "inert"
        return SimpleNamespace(status="ok", message="", sites=[])

    rover.sonar.scan = scan

    _run_rover(game, rover)

    assert placed[0] == (
        "survey.rover_1.base",
        0,
        0,
        "Base",
        "star",
        "accent",
        "All rover coordinates start here.",
    )
    assert ("survey.rover_1.c:-30:40", -30, 40, "inert", "circle", "neutral", "") in placed
