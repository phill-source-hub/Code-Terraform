"""Adapter tests: the Bio Exchange script against a fake exchange, input port and Inventory."""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent
from tests.harness.loop import StopOnSleep, run_loop, stop_after

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "bio_exchange_1.py"


def ok(**extra):
    return SimpleNamespace(status="ok", message="", **extra)


def order(order_id, status="available"):
    return SimpleNamespace(id=order_id, status=status)


def exchange(
    active=None, orders=(), matches=lambda item, props: True, record=None, deliver_status="ok"
):
    record = record if record is not None else []
    return SimpleNamespace(
        input=SimpleNamespace(
            connect=lambda target: record.append(("connect", target)) or ok(),
            take=lambda item, qty, props=None, mode=None: (
                record.append(("take", item, qty, props, mode)) or ok()
            ),
        ),
        active_order=lambda: active,
        orders=lambda: list(orders),
        set_order=lambda order_id: record.append(("set_order", order_id)) or ok(),
        clear_order=lambda: record.append(("clear_order",)) or ok(),
        matches_order=matches,
        deliver=lambda: (
            record.append(("deliver",)) or SimpleNamespace(status=deliver_status, message="")
        ),
    ), record


def inventory_with(stacks):
    game_inventory = FakeComponent(
        id="inventory",
        type_id="inventory",
        methods={"stacks": lambda: list(stacks)},
    )
    return game_inventory


def run(owner, stacks=()):
    game = StopOnSleep()
    game.components["inventory"] = inventory_with(stacks)
    run_loop(SCRIPT, game, owner)
    return game


def test_assigns_first_open_order_when_none_is_active():
    owner, record = exchange(
        active=None, orders=[order("bio_order_01", "complete"), order("bio_order_02")]
    )
    owner.set_order = stop_after(record, name="set_order")
    run(owner)
    assert record[-1][0] == "set_order"
    assert record[-1][1] == ("bio_order_02",)


def test_clears_a_completed_active_order():
    owner, record = exchange(active=order("bio_order_01", "complete"))
    owner.clear_order = stop_after(record, name="clear_order")
    run(owner)
    assert record[-1][0] == "clear_order"


def test_takes_matching_sample_then_delivers_it():
    stack = SimpleNamespace(id="sample_gw", count=1, properties={"glow": 2})
    owner, record = exchange(active=order("bio_order_01", "active"))
    owner.deliver = stop_after(record, name="deliver")
    run(owner, stacks=[stack])
    assert ("take", "sample_gw", 1, {"glow": 2}, "exact") in record
    assert record[-1][0] == "deliver"


def test_skips_samples_that_do_not_match_the_order():
    stack = SimpleNamespace(id="sample_wrong", count=1, properties=None)
    owner, record = exchange(
        active=order("bio_order_01", "active"), matches=lambda item, props: False
    )
    game = run(owner, stacks=[stack])
    assert all(entry[0] != "take" for entry in record)
    assert game.statuses[-1] == ("waiting for samples", "info")


def test_order_completion_is_reported():
    stack = SimpleNamespace(id="sample_gw", count=1, properties=None)
    owner, record = exchange(active=order("bio_order_01", "active"), deliver_status="complete")
    game = run(owner, stacks=[stack])
    assert game.statuses[-1] == ("order complete", "info")


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
