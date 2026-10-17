"""Adapter tests: the Bio Collector script against fake scan, collect and exchange."""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent
from tests.harness.loop import StopOnSleep, run_loop, stop_after

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "bio_collector_1.py"


def loc(coords, cataloged=False, fragment_id=None, distance=1.0):
    return SimpleNamespace(
        coords=coords, cataloged=cataloged, fragment_id=fragment_id, distance=distance
    )


def collector(locations, cargo=None, collect_status="ok"):
    calls: list = []

    def collect(coords):
        calls.append(coords)
        return SimpleNamespace(status=collect_status, message="")

    def scan():
        return locations

    return SimpleNamespace(cargo=cargo, scan=scan, collect=collect), calls


def exchange_with(requires=None):
    game_exchange = FakeComponent(
        id="bio_exchange_1",
        type_id="bio_exchange",
        methods={
            "active_order": lambda: None if requires is None else SimpleNamespace(requires=requires)
        },
    )
    return game_exchange


def run(self_obj, locations_exchange=None):
    game = StopOnSleep()
    if locations_exchange is not None:
        game.components["bio_exchange_1"] = locations_exchange
    run_loop(SCRIPT, game, self_obj)
    return game


def test_collects_nearest_uncataloged_fragment():
    owner, calls = collector([loc([1.0, 2.0]), loc([3.0, 4.0])])
    owner.collect = stop_after(calls)
    run(owner)
    assert calls[0][1] == ([1.0, 2.0],)


def test_skips_cataloged_fragments_when_an_uncataloged_one_exists():
    locations = [loc([0.0, 0.0], cataloged=True, fragment_id="gw_jaw_fang"), loc([5.0, 5.0])]
    owner, calls = collector(locations)
    owner.collect = stop_after(calls)
    run(owner)
    assert calls[0][1] == ([5.0, 5.0],)


def test_falls_back_to_the_fragment_an_active_order_requires():
    locations = [
        loc([0.0, 0.0], cataloged=True, fragment_id="gw_jaw_fang"),
        loc([9.0, 9.0], cataloged=True, fragment_id="gw_cardiac_node"),
    ]
    owner, calls = collector(locations)
    owner.collect = stop_after(calls)
    run(owner, exchange_with(requires={"gw_cardiac_node": 2}))
    assert calls[0][1] == ([9.0, 9.0],)


def test_does_not_collect_while_cargo_is_waiting():
    owner, calls = collector([loc([1.0, 1.0])], cargo=SimpleNamespace())
    scanned: list = []
    owner.scan = lambda: scanned.append(True) or []
    run(owner)
    assert calls == [] and scanned == []


def test_reports_no_target_when_nothing_is_left_to_collect():
    owner, calls = collector([loc([0.0, 0.0], cataloged=True, fragment_id="oc_cranium")])
    game = run(owner)
    assert calls == []
    assert game.statuses[-1] == ("no fragment to collect", "info")


def test_collect_failure_is_a_warning_and_sleeps():
    owner, calls = collector([loc([1.0, 1.0])], collect_status="busy")
    game = run(owner)
    assert game.statuses[-1] == ("collect busy", "warn")
    assert game.clock.now == 60.0


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
