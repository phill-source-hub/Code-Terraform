"""Tests for the Control Room card scripts: what each card draws for a given set of game objects.

Each card runs one full pass (one clear() call per tick, stopped on the second) against stub-shaped
fake objects and the fake panel from tests/harness/fake_panel.py.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.harness.fake_comms import FakeSignalBus
from tests.harness.fake_game import FakeGame
from tests.harness.fake_panel import FakePanel
from tests.harness.loop import run_loop

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "scripts" / "cards"
sys.path.insert(0, str(ROOT / "scripts" / "libs"))


def _run(card, panel, **components):
    game = FakeGame()
    for name, value in components.items():
        game.components[name] = value
    run_loop(CARDS / card, game, owner=None, extra={"panel": panel})
    return panel


def _grid(anchor, net, stored, capacity=100.0, reserve=0.0, reserve_cap=0.0):
    return SimpleNamespace(
        anchor_id=anchor,
        net=net,
        stored=stored,
        capacity=capacity,
        reserve_stored=reserve,
        reserve_capacity=reserve_cap,
    )


def _power(*grids):
    total = SimpleNamespace(
        net=sum(g.net for g in grids),
        stored=sum(g.stored for g in grids),
        capacity=sum(g.capacity for g in grids),
        reserve_stored=0.0,
        reserve_capacity=0.0,
    )
    return SimpleNamespace(grids=lambda: list(grids), total=lambda: total)


# D2 power runway ---------------------------------------------------------------------------


def test_d2_critical_grid_is_red_and_shows_its_runway():
    panel = _run(
        "d2_power_runway.py", FakePanel(), power_control=_power(_grid("base", -200.0, 100.0))
    )

    assert any(args[3] == "error" for args in panel.named("status_dot"))
    assert "runway 0.5 h" in panel.texts()
    assert "base" in panel.texts()


def test_d2_grid_that_is_not_draining_reads_not_draining():
    panel = _run("d2_power_runway.py", FakePanel(), power_control=_power(_grid("base", 10.0, 50.0)))

    assert "not draining" in panel.texts()


def test_d2_without_power_control_says_so():
    panel = _run("d2_power_runway.py", FakePanel(), power_control=None)

    assert "Power control not available" in panel.texts()


def test_d2_names_grids_beyond_the_four_columns():
    grids = [_grid("g" + str(i), 10.0, 50.0) for i in range(6)]
    panel = _run("d2_power_runway.py", FakePanel(), power_control=_power(*grids))

    assert "2 more grids not shown" in panel.texts()


# D3 fleet board ---------------------------------------------------------------------------


def _rover(name, status, wh=50.0, cap=100.0):
    return SimpleNamespace(name=name, status=status, battery_wh=wh, battery_capacity=cap)


def _drone(name, status, engine="electric", wh=20.0, cap=40.0, tons=None, tons_cap=None):
    return SimpleNamespace(
        name=name,
        status=status,
        engine=engine,
        battery_wh=wh if engine != "heli" else None,
        battery_capacity=cap if engine != "heli" else None,
        oil_tons=tons,
        oil_capacity=tons_cap,
    )


def test_d3_problem_units_sort_to_the_top():
    fleet = SimpleNamespace(
        vehicles=lambda: [_rover("zeta", "idle"), _rover("alpha", "stranded")],
        drones=lambda: [_drone("beta", "traveling")],
    )
    panel = _run("d3_fleet_board.py", FakePanel(), fleet=fleet)

    names = [args[2] for args in panel.named("draw_text") if args[2] in ("alpha", "zeta", "beta")]
    assert names == ["alpha", "beta", "zeta"]


def test_d3_heli_drone_bar_uses_oil_not_battery():
    fleet = SimpleNamespace(
        vehicles=lambda: [],
        drones=lambda: [_drone("heli_1", "traveling", engine="heli", tons=5.0, tons_cap=10.0)],
    )
    panel = _run("d3_fleet_board.py", FakePanel(), fleet=fleet)

    bars = panel.named("progress_bar")
    assert bars[0][4] == pytest.approx(0.5)


def test_d3_empty_fleet_says_so():
    fleet = SimpleNamespace(vehicles=lambda: [], drones=lambda: [])
    panel = _run("d3_fleet_board.py", FakePanel(), fleet=fleet)

    assert "No vehicles or drones yet" in panel.texts()


# D6 Earth Orders ---------------------------------------------------------------------------


def _order(name, requires, shipped, reward=0):
    return SimpleNamespace(name=name, requires=requires, shipped=shipped, reward_credits=reward)


def test_d6_current_order_shows_progress_and_units():
    orders = SimpleNamespace(
        list_orders=lambda: [_order("Iron run", {"iron_ingot": 10}, {"iron_ingot": 5})],
        list_upcoming_orders=lambda: [],
    )
    panel = _run("d6_earth_orders.py", FakePanel(), orders=orders)

    assert panel.named("progress_bar")[0][4] == pytest.approx(0.5)
    assert "5 / 10" in panel.texts()
    assert "Nothing queued" in panel.texts()


def test_d6_upcoming_order_shows_reward():
    orders = SimpleNamespace(
        list_orders=lambda: [],
        list_upcoming_orders=lambda: [_order("Next", {"water": 4}, {}, reward=300)],
    )
    panel = _run("d6_earth_orders.py", FakePanel(), orders=orders)

    assert "300 cr" in panel.texts()
    assert "No contractor shipment right now" in panel.texts()


def test_d6_without_orders_component_says_so():
    panel = _run("d6_earth_orders.py", FakePanel(), orders=None)

    assert "Earth Orders not available" in panel.texts()


# D9 Signal Bus monitor ---------------------------------------------------------------------


def test_d9_invalid_channel_gets_a_hint_and_no_bus_read():
    panel = FakePanel()
    panel.values["bus.channel"] = "bad channel!"
    panel = _run("d9_signal_bus.py", panel, comms=FakeSignalBus().as_component())

    assert any("Use letters, digits" in text for text in panel.texts())
    assert not any("pending" in text for text in panel.texts())


def test_d9_lists_pending_messages_on_the_channel():
    bus = FakeSignalBus()
    bus.send("ctrl.rover_1.dispatch", {"task": "nearest"})
    panel = FakePanel()
    panel.values["bus.channel"] = "ctrl.rover_1.dispatch"
    panel = _run("d9_signal_bus.py", panel, comms=bus.as_component())

    assert "1 pending" in panel.texts()
    assert any(text.startswith("#1 test t0 ") for text in panel.texts())


def test_d9_without_research_says_so():
    panel = _run("d9_signal_bus.py", FakePanel(), comms=None)

    assert "Signal Bus not researched yet" in panel.texts()


# D1 base overview ---------------------------------------------------------------------------


class _Atmosphere:
    def __init__(self, o2=None, o2_missing=False):
        self._o2 = o2
        self._o2_missing = o2_missing

    def get_o2(self):
        if self._o2_missing:
            raise ValueError("oxygen sensor not repaired")
        return self._o2

    def get_n2(self):
        return 780.0

    def get_pressure(self):
        return 101.0


def test_d1_missing_oxygen_sensor_reads_unavailable_and_alerts():
    power = _power(_grid("base", 50.0, 100.0))
    panel = _run(
        "d1_base_overview.py",
        FakePanel(width=1000, height=400),
        power_control=power,
        atmosphere=_Atmosphere(o2_missing=True),
    )

    assert "O2 unavailable" in panel.texts()
    assert "Oxygen sensor not repaired: O2 reads unavailable" in panel.texts()


def test_d1_counts_problem_units_in_the_fleet_summary():
    fleet = SimpleNamespace(
        vehicles=lambda: [_rover("r", "stranded")],
        drones=lambda: [_drone("d", "traveling")],
    )
    panel = _run(
        "d1_base_overview.py",
        FakePanel(width=1000, height=400),
        power_control=_power(_grid("base", 50.0, 100.0)),
        atmosphere=_Atmosphere(o2=210.0),
        fleet=fleet,
    )

    assert "attention 1   waiting 0   ok 1" in panel.texts()
    assert "1 vehicle or drone needs attention" in panel.texts()


def test_d1_without_power_data_says_so_and_never_claims_nominal():
    panel = _run("d1_base_overview.py", FakePanel(width=1000, height=400))

    assert "BASE OVERVIEW" in [args[4] for args in panel.named("card")]
    assert "No power data" in panel.texts()
    assert "All systems nominal" not in panel.texts()
