"""Adapter tests: the Bio Collector script against fake scan, collect, Exchange, Lab and Inventory.

A run ends at the first collect() call (first_collect) or at the first sleep (StopOnSleep, the
idle or blocked path), so each test asserts one decision.
"""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent
from tests.harness.loop import StopOnSleep, run_loop, stop_after

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "bio_collector_1.py"
BIOME = "frozen"


class _UnreadableLab:
    """A Bio Lab whose chamber cannot be read from another script."""

    id = "bio_lab_1"

    @property
    def specimen(self):
        raise AttributeError("specimen not readable")


def loc(coords, cataloged=False, fragment_id=None, distance=1.0):
    return SimpleNamespace(
        coords=coords, cataloged=cataloged, fragment_id=fragment_id, distance=distance
    )


def order(requires, delivered=None, in_transit=None, status="active", biome=BIOME):
    return SimpleNamespace(
        id="order",
        biome=biome,
        status=status,
        requires=requires,
        delivered=delivered or {},
        in_transit=in_transit or {},
    )


def specimen(coords, fragment_id=None):
    return SimpleNamespace(coords=coords, fragment_id=fragment_id)


def setup(
    locations,
    orders=(),
    stock=None,
    cargo=None,
    lab_specimen=None,
    lab_unreadable=False,
    collect_status="ok",
    with_exchange=True,
):
    """Returns (owner, game)."""
    stock = stock or {}
    owner = SimpleNamespace(
        cargo=cargo,
        scan=lambda: locations,
        collect=lambda coords: SimpleNamespace(status=collect_status, message=""),
        outpost=SimpleNamespace(biome=BIOME),
    )
    game = StopOnSleep()
    game.components["inventory"] = FakeComponent(
        id="inventory",
        type_id="inventory",
        methods={"count": lambda item_id: stock.get(item_id, 0)},
    )
    if with_exchange:
        game.components["bio_exchange_1"] = FakeComponent(
            id="bio_exchange_1",
            type_id="bio_exchange",
            methods={"orders": lambda: list(orders)},
        )
    if lab_unreadable:
        game.components["bio_lab_1"] = _UnreadableLab()
    else:
        game.components["bio_lab_1"] = SimpleNamespace(id="bio_lab_1", specimen=lab_specimen)
    return owner, game


def first_collect(owner, game):
    """Runs the script and returns the coords of its first collect() call, or None."""
    recorded: list = []
    owner.collect = stop_after(recorded)
    run_loop(SCRIPT, game, owner)
    return recorded[0][1][0] if recorded else None


def test_explores_nearest_uncataloged_fragment_when_no_order_needs_anything():
    owner, game = setup([loc([1.0, 2.0]), loc([3.0, 4.0])])
    assert first_collect(owner, game) == [1.0, 2.0]


def test_stops_exploring_when_every_location_is_identified_and_no_order_is_open():
    owner, game = setup([loc([0.0, 0.0], True, "gw_a"), loc([5.0, 5.0], True, "gw_b")])
    assert first_collect(owner, game) is None
    assert game.statuses[-1] == ("no fragment to collect for the open Bio Orders", "info")


def test_collects_a_cataloged_fragment_the_open_order_still_needs():
    locations = [loc([0.0, 0.0], True, "gw_jaw_fang"), loc([5.0, 5.0])]
    owner, game = setup(locations, orders=[order({"gw_jaw_fang": 2})])
    assert first_collect(owner, game) == [0.0, 0.0]


def test_once_a_required_fragment_is_in_stock_the_next_required_one_is_collected():
    # Regression: the old script kept collecting the first required fragment after it was
    # cataloged, because it never subtracted units already held.
    locations = [loc([0.0, 0.0], True, "gw_a"), loc([9.0, 9.0], True, "gw_b")]
    owner, game = setup(locations, orders=[order({"gw_a": 1, "gw_b": 1})], stock={"gw_a": 1})
    assert first_collect(owner, game) == [9.0, 9.0]


def test_units_delivered_or_in_transit_are_not_collected_again():
    locations = [loc([0.0, 0.0], True, "gw_a")]
    owner, game = setup(
        locations, orders=[order({"gw_a": 2}, delivered={"gw_a": 1}, in_transit={"gw_a": 1})]
    )
    assert first_collect(owner, game) is None


def test_specimen_in_the_lab_chamber_counts_toward_the_order():
    locations = [loc([0.0, 0.0], True, "gw_a")]
    owner, game = setup(
        locations, orders=[order({"gw_a": 1})], lab_specimen=specimen([0.0, 0.0], "gw_a")
    )
    assert first_collect(owner, game) is None


def test_unidentified_specimen_in_the_lab_is_matched_to_its_location_by_coords():
    locations = [loc([0.0, 0.0], True, "gw_a"), loc([7.0, 7.0])]
    owner, game = setup(
        locations, orders=[order({"gw_a": 1})], lab_specimen=specimen([0.0, 0.0], None)
    )
    assert first_collect(owner, game) == [7.0, 7.0]


def test_an_unreadable_lab_chamber_is_ignored_not_fatal():
    locations = [loc([0.0, 0.0], True, "gw_a")]
    owner, game = setup(locations, orders=[order({"gw_a": 1})], lab_unreadable=True)
    assert first_collect(owner, game) == [0.0, 0.0]


def test_the_largest_shortfall_across_orders_is_used_not_the_sum():
    locations = [loc([0.0, 0.0], True, "gw_a")]
    owner, game = setup(locations, orders=[order({"gw_a": 1}), order({"gw_a": 1})])
    recorded: list = []
    owner.collect = stop_after(recorded)
    run_loop(SCRIPT, game, owner)
    assert recorded[0][1][0] == [0.0, 0.0]


def test_orders_for_another_biome_are_ignored():
    locations = [loc([0.0, 0.0], True, "gw_a"), loc([4.0, 4.0])]
    owner, game = setup(locations, orders=[order({"gw_a": 1}, biome="volcanic")])
    assert first_collect(owner, game) == [4.0, 4.0]


def test_completed_orders_are_ignored():
    locations = [loc([0.0, 0.0], True, "gw_a"), loc([4.0, 4.0])]
    owner, game = setup(locations, orders=[order({"gw_a": 1}, status="complete")])
    assert first_collect(owner, game) == [4.0, 4.0]


def test_holds_its_specimen_while_cargo_is_occupied():
    owner, game = setup([loc([1.0, 2.0])], cargo=specimen([1.0, 2.0]))
    assert first_collect(owner, game) is None
    assert game.statuses[-1] == ("holding a specimen for the Bio Lab", "info")


def test_busy_collect_is_retried_after_a_short_pause():
    owner, game = setup([loc([1.0, 2.0])], collect_status="busy")
    run_loop(SCRIPT, game, owner)
    assert game.clock.now == 5


def test_refused_collect_is_a_warning_and_waits_longer():
    owner, game = setup([loc([1.0, 2.0])], collect_status="cargo_occupied")
    run_loop(SCRIPT, game, owner)
    assert game.statuses[-1][1] == "warn"
    assert game.clock.now == 60


def test_idle_when_nothing_is_left_to_collect():
    locations = [loc([0.0, 0.0], True, "gw_a")]
    owner, game = setup(locations, orders=[order({"gw_a": 1})], stock={"gw_a": 1})
    run_loop(SCRIPT, game, owner)
    assert game.statuses[-1] == ("no fragment to collect for the open Bio Orders", "info")


def test_explores_when_there_is_no_exchange():
    owner, game = setup([loc([1.0, 2.0])], with_exchange=False)
    assert first_collect(owner, game) == [1.0, 2.0]


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
