"""Adapter tests: the Bio Exchange script against a stateful fake exchange, its ports, Inventory and
Bio Orders.

Units move the way the game moves them: the input latches to one item id, delivered samples
count toward `delivered`, samples staged in the input count toward `in_transit`, and an order
that is filled reads as complete. Every action and every sleep is a tick, so a run ends after
`budget` ticks and the test checks the machines' final state and the action order.
"""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame
from tests.harness.loop import ScriptStop, run_loop

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "bio_exchange_1.py"
VARIANT = {"glow": 1}  # a processed sample: an order that needs it rejects plain stock


def ok(**extra):
    return SimpleNamespace(status="ok", message="", **extra)


def status(value, **extra):
    return SimpleNamespace(status=value, message="", **extra)


def stack(item_id, count, properties=None):
    return SimpleNamespace(id=item_id, count=count, properties=properties)


def bio_order(order_id, name, requires, variant=False, delivered=None, complete=False):
    return SimpleNamespace(
        id=order_id,
        name=name,
        requires=dict(requires),
        delivered=dict(delivered or {}),
        variant=variant,
        complete=complete,
    )


def _same(s, item_id, properties):
    return s.id == item_id and s.properties == properties


def _add(stacks, item_id, count, properties=None):
    for s in stacks:
        if _same(s, item_id, properties):
            s.count += count
            return
    stacks.append(stack(item_id, count, properties))


def _remove(stacks, item_id, count, properties=None):
    moved = 0
    for s in stacks:
        if _same(s, item_id, properties) and moved < count:
            take = min(s.count, count - moved)
            s.count -= take
            moved += take
    stacks[:] = [s for s in stacks if s.count > 0]
    return moved


class _Input:
    def __init__(self, exchange):
        self.exchange = exchange

    def connect(self, target):
        self.exchange.tick("input.connect")
        return ok()

    def take(self, item_id, count, properties=None, mode=None):
        self.exchange.tick("input.take")
        staged = self.exchange.input_stacks
        if any(s.id != item_id and s.count > 0 for s in staged):
            return status("target_wrong_material", requested=count, moved=0)
        available = sum(s.count for s in self.exchange.inventory if _same(s, item_id, properties))
        moved = min(count, available)
        if moved == 0:
            return status("source_empty", requested=count, moved=0)
        _remove(self.exchange.inventory, item_id, moved, properties)
        _add(staged, item_id, moved, properties)
        return status("ok" if moved == count else "partial", requested=count, moved=moved)

    def eject(self, destination, item_id, count, properties=None, mode=None):
        self.exchange.tick("input.eject")
        moved = _remove(self.exchange.input_stacks, item_id, count, properties)
        _add(self.exchange.inventory, item_id, moved, properties)
        return status("ok", requested=count, moved=moved)

    def stacks(self):
        return [stack(s.id, s.count, s.properties) for s in self.exchange.input_stacks]


class _Output:
    def __init__(self, exchange):
        self.exchange = exchange

    def connect(self, target):
        self.exchange.tick("output.connect")
        return ok()

    def send(self, item_id, count, properties=None, mode=None):
        self.exchange.tick("output.send")
        moved = _remove(self.exchange.output_stacks, item_id, count, properties)
        _add(self.exchange.inventory, item_id, moved, properties)
        return status("ok", requested=count, moved=moved)

    def stacks(self):
        return [stack(s.id, s.count, s.properties) for s in self.exchange.output_stacks]


class FakeExchange:
    """The Bio Exchange's own API (self) over shared fake state."""

    def __init__(
        self, orders, inventory=(), active=None, input_stacks=(), output_stacks=(), budget=60
    ):
        self.orders_by_id = {o.id: o for o in orders}
        self.active_id = active
        self.inventory = [stack(s.id, s.count, s.properties) for s in inventory]
        self.input_stacks = [stack(s.id, s.count, s.properties) for s in input_stacks]
        self.output_stacks = [stack(s.id, s.count, s.properties) for s in output_stacks]
        self.actions: list = []
        self.budget = budget
        self.deliver_refuses = False
        self.input = _Input(self)
        self.output = _Output(self)

    def tick(self, name):
        self.actions.append(name)
        if len(self.actions) > self.budget:
            raise ScriptStop

    def _snapshot(self, order):
        in_transit = {}
        for s in self.input_stacks:
            if s.id in order.requires and self._accepts(order, s.id, s.properties):
                in_transit[s.id] = in_transit.get(s.id, 0) + s.count
        if order.complete:
            status_value = "complete"
        elif order.id == self.active_id:
            status_value = "active"
        else:
            status_value = "available"
        return SimpleNamespace(
            id=order.id,
            name=order.name,
            biome="frozen",
            requires=dict(order.requires),
            delivered=dict(order.delivered),
            in_transit=in_transit,
            status=status_value,
        )

    def _accepts(self, order, item_id, properties):
        if item_id not in order.requires or order.complete:
            return False
        return properties == (VARIANT if order.variant else None)

    def orders(self):
        return [self._snapshot(o) for o in self.orders_by_id.values()]

    def active_order(self):
        if self.active_id is None:
            return None
        return self._snapshot(self.orders_by_id[self.active_id])

    def set_order(self, order_id):
        self.tick("set_order")
        order = self.orders_by_id.get(order_id)
        if order is None:
            return status("unknown_order")
        if order.complete:
            return status("completed")
        self.active_id = order_id
        return ok()

    def clear_order(self):
        self.tick("clear_order")
        self.active_id = None
        return ok()

    def matches_order(self, item_id, properties=None):
        if self.active_id is None:
            return False
        return self._accepts(self.orders_by_id[self.active_id], item_id, properties)

    def deliver(self):
        self.tick("deliver")
        if self.deliver_refuses:
            return status("no_input")
        if self.active_id is None:
            return status("no_active")
        order = self.orders_by_id[self.active_id]
        for s in self.input_stacks:
            if s.count > 0 and self._accepts(order, s.id, s.properties):
                _remove(self.input_stacks, s.id, 1, s.properties)
                order.delivered[s.id] = order.delivered.get(s.id, 0) + 1
                if order.delivered == order.requires:
                    order.complete = True
                    return status("complete")
                return ok()
        return status("no_input")


def drive(exchange, inventory_available=True):
    """Runs the Exchange script until its tick budget ends it. Returns the game."""
    game = _TickingGame(exchange)
    if inventory_available:
        game.components["inventory"] = FakeComponent(
            id="inventory",
            type_id="inventory",
            methods={
                "stacks": lambda: [
                    stack(s.id, s.count, s.properties) for s in exchange.inventory if s.count > 0
                ]
            },
        )
    run_loop(SCRIPT, game, exchange)
    return game


class _TickingGame(FakeGame):
    def __init__(self, exchange):
        super().__init__()
        self.exchange = exchange

    def sleep(self, seconds, /):
        super().sleep(seconds)
        self.exchange.tick("sleep")


def stock(exchange, item_id, properties=None):
    return sum(s.count for s in exchange.inventory if _same(s, item_id, properties))


def test_fills_a_multi_item_order_one_fragment_at_a_time_until_it_is_complete():
    order = bio_order("o1", "Frozen Census", {"gw_a": 1, "gw_b": 1})
    exchange = FakeExchange(
        [order],
        inventory=[stack("gw_a", 1), stack("gw_b", 1)],
        budget=30,
    )
    drive(exchange)
    assert order.complete
    assert order.delivered == {"gw_a": 1, "gw_b": 1}
    assert exchange.input_stacks == []
    assert exchange.inventory == []


def test_a_staged_sample_deliver_refuses_is_returned_not_retried_forever():
    # Regression: no_input was treated as transient, so the same staged sample was retried
    # every few seconds and the Exchange input stayed full.
    order = bio_order("o1", "Frozen Census", {"gw_a": 2})
    # Budget 3: deliver, eject, then the 60 s pause. The run ends before the next restage.
    exchange = FakeExchange([order], active="o1", input_stacks=[stack("gw_a", 3)], budget=3)
    exchange.deliver_refuses = True
    game = drive(exchange)
    assert exchange.actions[:3] == ["deliver", "input.eject", "sleep"]
    assert exchange.input_stacks == []
    assert stock(exchange, "gw_a") == 3
    assert ("deliver no_input for gw_a: returned to Inventory", "warn") in game.statuses


def test_a_restart_with_a_staged_sample_delivers_it_instead_of_getting_stuck():
    order = bio_order("o1", "Frozen Census", {"gw_a": 2})
    exchange = FakeExchange(
        [order],
        active="o1",
        input_stacks=[stack("gw_a", 1)],
        inventory=[stack("gw_a", 1)],
        budget=10,
    )
    drive(exchange)
    assert order.delivered == {"gw_a": 2}
    assert stock(exchange, "gw_a") == 0


def test_units_already_staged_or_delivered_are_not_taken_again():
    order = bio_order("o1", "Frozen Census", {"gw_a": 2}, delivered={"gw_a": 1})
    exchange = FakeExchange([order], active="o1", inventory=[stack("gw_a", 5)], budget=10)
    drive(exchange)
    # Only one more unit was needed, so one was taken and delivered; four stay in stock.
    assert order.complete
    assert order.delivered == {"gw_a": 2}
    assert stock(exchange, "gw_a") == 4


def test_take_is_capped_by_what_the_order_still_needs():
    order = bio_order("o1", "Frozen Census", {"gw_a": 2})
    # Budget 2: the take and its connect run, and the run ends before the first deliver.
    exchange = FakeExchange([order], active="o1", inventory=[stack("gw_a", 5)], budget=2)
    drive(exchange)
    assert sum(s.count for s in exchange.input_stacks) == 2
    assert stock(exchange, "gw_a") == 3


def test_a_surplus_in_the_output_is_shipped_to_inventory_first():
    order = bio_order("o1", "Frozen Census", {"gw_a": 1})
    exchange = FakeExchange([order], active="o1", output_stacks=[stack("gw_a", 1)], budget=2)
    drive(exchange)
    assert exchange.actions[:2] == ["output.connect", "output.send"]
    assert exchange.output_stacks == []


def test_a_staged_sample_for_an_order_completed_elsewhere_goes_back_to_inventory():
    order = bio_order("o1", "Frozen Census", {"gw_a": 1}, delivered={"gw_a": 1}, complete=True)
    exchange = FakeExchange([order], active="o1", input_stacks=[stack("gw_a", 1)], budget=6)
    drive(exchange)
    assert "deliver" not in exchange.actions
    assert exchange.input_stacks == []
    assert stock(exchange, "gw_a") == 1
    assert "clear_order" in exchange.actions


def test_a_stray_sample_in_the_input_is_ejected_not_flushed():
    order = bio_order("o1", "Frozen Census", {"gw_a": 1})
    exchange = FakeExchange([order], active="o1", input_stacks=[stack("gw_z", 2)], budget=4)
    drive(exchange)
    assert "input.eject" in exchange.actions
    assert stock(exchange, "gw_z") == 2


def test_an_order_that_needs_a_variant_this_exchange_cannot_make_is_passed_over():
    variant_order = bio_order("o1", "Coastal Glow", {"gw_a": 1}, variant=True)
    plain_order = bio_order("o2", "Frozen Census", {"gw_b": 1})
    exchange = FakeExchange(
        [variant_order, plain_order],
        inventory=[stack("gw_a", 1), stack("gw_b", 1)],
        budget=30,
    )
    drive(exchange)
    assert plain_order.complete
    assert not variant_order.complete
    assert stock(exchange, "gw_a") == 1


def test_a_variant_order_is_filled_from_matching_variant_stock():
    order = bio_order("o1", "Coastal Glow", {"gw_a": 1}, variant=True)
    exchange = FakeExchange([order], inventory=[stack("gw_a", 1, VARIANT)], budget=20)
    drive(exchange)
    assert order.complete


def test_no_open_order_waits_and_assigns_nothing():
    order = bio_order("o1", "Frozen Census", {"gw_a": 1}, complete=True)
    exchange = FakeExchange([order], inventory=[stack("gw_a", 1)], budget=3)
    game = drive(exchange)
    assert "set_order" not in exchange.actions
    assert game.statuses[-1] == ("no open Bio Order that Inventory can fill", "info")


def test_missing_inventory_is_a_warning_not_a_crash():
    order = bio_order("o1", "Frozen Census", {"gw_a": 1})
    exchange = FakeExchange([order], budget=2)
    game = drive(exchange, inventory_available=False)
    assert ("inventory not found: the Bio Exchange needs home base", "warn") in game.statuses
    assert set(exchange.actions) == {"sleep"}


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
