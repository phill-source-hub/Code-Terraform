"""Adapter tests: the Bio Lab script against a stateful fake lab, its ports, Inventory, Shop and
the Bio Collector.

The fake keeps items where the game does: the input latches to one reagent id, transfers move
units rather than copy them, and extraction destroys loaded reagents on a wrong recipe. Every
action is a tick with a name; a run ends after `budget` ticks, so each test drives a fixed
number of passes and then checks what the machines hold and which actions ran in what order.
"""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame
from tests.harness.loop import ScriptStop, run_loop

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "bio_lab_1.py"
RECIPE = {"alkaline_buffer": 2, "cryo_solvent": 3}
PRICES = {"alkaline_buffer": 1, "cryo_solvent": 2}


def ok(**extra):
    return SimpleNamespace(status="ok", message="", **extra)


def status(value, **extra):
    return SimpleNamespace(status=value, message="", **extra)


def stack(item_id, count, properties=None):
    return SimpleNamespace(id=item_id, count=count, properties=properties)


def specimen(stage="analyzed", recipe=None):
    recipe = dict(RECIPE) if recipe is None and stage == "analyzed" else recipe
    return SimpleNamespace(stage=stage, recipe=recipe, fragment_id=None, coords=[0.0, 0.0])


def _add(stacks, item_id, count):
    for s in stacks:
        if s.id == item_id:
            s.count += count
            return
    stacks.append(stack(item_id, count))


def _remove(stacks, item_id, count):
    moved = 0
    for s in stacks:
        if s.id == item_id and moved < count:
            take = min(s.count, count - moved)
            s.count -= take
            moved += take
    stacks[:] = [s for s in stacks if s.count > 0]
    return moved


class _Input:
    def __init__(self, lab):
        self.lab = lab

    def connect(self, target):
        self.lab.tick("input.connect")
        return ok()

    def take(self, item_id, count, properties=None, mode=None):
        self.lab.tick("input.take")
        staged = self.lab.input_stacks
        if any(s.id != item_id and s.count > 0 for s in staged):
            return status("target_wrong_material", requested=count, moved=0)
        moved = min(count, self.lab.inventory.get(item_id, 0))
        if moved == 0:
            return status("source_empty", requested=count, moved=0)
        self.lab.inventory[item_id] -= moved
        _add(staged, item_id, moved)
        return status("ok" if moved == count else "partial", requested=count, moved=moved)

    def eject(self, destination, item_id, count, properties=None, mode=None):
        self.lab.tick("input.eject")
        moved = _remove(self.lab.input_stacks, item_id, count)
        self.lab.inventory[item_id] = self.lab.inventory.get(item_id, 0) + moved
        return status("ok", requested=count, moved=moved)

    def stacks(self):
        return [stack(s.id, s.count) for s in self.lab.input_stacks if s.count > 0]


class _Output:
    def __init__(self, lab):
        self.lab = lab

    def connect(self, target):
        self.lab.tick("output.connect")
        return ok()

    def send(self, item_id, count, properties=None, mode=None):
        self.lab.tick("output.send")
        if self.lab.send_refusal is not None:
            return status(self.lab.send_refusal, requested=count, moved=0)
        moved = _remove(self.lab.output_stacks, item_id, count)
        self.lab.inventory[item_id] = self.lab.inventory.get(item_id, 0) + moved
        return status("ok", requested=count, moved=moved)

    def stacks(self):
        return [stack(s.id, s.count) for s in self.lab.output_stacks if s.count > 0]


class FakeLab:
    """The Bio Lab's own API (self) over shared fake state."""

    def __init__(
        self,
        specimen_value=None,
        loaded=None,
        input_stacks=(),
        output_stacks=(),
        inventory=None,
        collector_stock=0,
        budget=60,
    ):
        self._specimen = specimen_value
        self.loaded_reagents = dict(loaded or {})
        self.input_stacks = [stack(s.id, s.count) for s in input_stacks]
        self.output_stacks = [stack(s.id, s.count) for s in output_stacks]
        self.inventory = dict(inventory or {})
        self.collector_stock = collector_stock
        self.send_refusal = None
        self.take_refusal = None
        self.analysis_refusal = None
        self.extract_refusal = None
        self.actions: list = []
        self.budget = budget
        self.input = _Input(self)
        self.output = _Output(self)

    def tick(self, name):
        self.actions.append(name)
        if len(self.actions) > self.budget:
            raise ScriptStop

    @property
    def specimen(self):
        return self._specimen

    def take_from(self, collector):
        self.tick("take_from")
        if self.take_refusal is not None:
            return status(self.take_refusal)
        if self._specimen is not None:
            return status("input_occupied")
        if self.collector_stock == 0:
            return status("source_empty")
        self.collector_stock -= 1
        self._specimen = specimen(stage="collected", recipe=None)
        return ok()

    def analyze(self):
        self.tick("analyze")
        if self.analysis_refusal is not None:
            return status(self.analysis_refusal)
        if self._specimen is None:
            return status("input_empty")
        self._specimen.stage = "analyzed"
        self._specimen.recipe = dict(RECIPE)
        info = SimpleNamespace(name="Jaw Fang", fragment_id="gw_jaw_fang", required_recipe=RECIPE)
        return ok(info=info)

    def load(self, reagent_id, qty, properties=None, property_match=None):
        self.tick("load")
        if sum(s.count for s in self.input_stacks if s.id == reagent_id) < qty:
            return status("insufficient_input")
        _remove(self.input_stacks, reagent_id, qty)
        self.loaded_reagents[reagent_id] = self.loaded_reagents.get(reagent_id, 0) + qty
        return ok()

    def unload_reagents(self):
        self.tick("unload_reagents")
        if not self.loaded_reagents:
            return status("empty")
        for reagent_id, qty in self.loaded_reagents.items():
            _add(self.output_stacks, reagent_id, qty)
        self.loaded_reagents = {}
        return ok()

    def extract(self):
        self.tick("extract")
        if self.extract_refusal is not None:
            return status(self.extract_refusal)
        if self._specimen is None:
            return status("input_empty")
        if self.loaded_reagents != RECIPE:
            self.loaded_reagents = {}  # the game destroys the wrong reagents
            return status("recipe_mismatch")
        self.loaded_reagents = {}
        _add(self.output_stacks, "gw_jaw_fang", 1)
        return ok()

    def discard(self):
        self.tick("discard")
        if self._specimen is None:
            return status("input_empty")
        self._specimen = None
        return ok()


class FakeShop:
    def __init__(self, lab, credits):
        self.lab = lab
        self.credits = credits
        self.purchases: list = []

    def buy(self, item_id, quantity=1):
        self.lab.tick("shop.buy")
        cost = PRICES[item_id] * quantity
        if cost > self.credits:
            return status("insufficient_credits")
        self.credits -= cost
        self.purchases.append((item_id, quantity))
        self.lab.inventory[item_id] = self.lab.inventory.get(item_id, 0) + quantity
        return ok()


class _TickingGame(FakeGame):
    """Sleep counts as a tick too, so a pass that only waits still ends at the budget."""

    def __init__(self, lab):
        super().__init__()
        self.lab = lab

    def sleep(self, seconds, /):
        super().sleep(seconds)
        self.lab.tick("sleep")


def drive(lab, credits=100, with_collector=True, with_inventory=True):
    """Runs the Lab script until its tick budget ends it. Returns (game, shop)."""
    game = _TickingGame(lab)
    shop = FakeShop(lab, credits)
    game.components["shop"] = FakeComponent(id="shop", type_id="shop", methods={"buy": shop.buy})
    if with_collector:
        game.components["bio_collector_1"] = FakeComponent(
            id="bio_collector_1", type_id="bio_collector", methods={}
        )
    if with_inventory:
        game.components["inventory"] = FakeComponent(
            id="inventory",
            type_id="inventory",
            methods={"count": lambda item_id: lab.inventory.get(item_id, 0)},
        )
    run_loop(SCRIPT, game, lab)
    return game, shop


def sample_count(lab):
    return lab.inventory.get("gw_jaw_fang", 0)


def test_full_cycle_buys_the_shortfall_extracts_once_and_ships_the_sample():
    lab = FakeLab(inventory={"alkaline_buffer": 5}, collector_stock=1, budget=40)
    game, shop = drive(lab)
    assert sample_count(lab) == 1
    assert lab.specimen is None
    assert lab.output_stacks == []
    assert lab.input_stacks == []
    assert lab.loaded_reagents == {}
    assert shop.purchases == [("cryo_solvent", 3)]
    assert shop.credits == 94
    assert lab.actions.count("extract") == 1


def test_does_not_buy_what_inventory_already_holds():
    lab = FakeLab(inventory={"alkaline_buffer": 5, "cryo_solvent": 3}, collector_stock=1, budget=40)
    game, shop = drive(lab)
    assert shop.purchases == []
    assert sample_count(lab) == 1


def test_insufficient_credits_keeps_the_specimen_and_warns():
    lab = FakeLab(inventory={"alkaline_buffer": 5}, collector_stock=1, budget=20)
    game, shop = drive(lab, credits=1)
    assert lab.specimen is not None
    assert "extract" not in lab.actions
    assert sample_count(lab) == 0
    assert ("buy cryo_solvent: insufficient_credits", "warn") in game.statuses
    assert "warning: buy cryo_solvent: insufficient_credits\n" in game.printed


def test_restart_resumes_from_partly_staged_reagents_without_buying_twice():
    lab = FakeLab(
        specimen_value=specimen(),
        loaded={"alkaline_buffer": 2},
        input_stacks=[stack("cryo_solvent", 1)],
        inventory={"cryo_solvent": 2},
        budget=40,
    )
    game, shop = drive(lab)
    assert shop.purchases == []
    assert sample_count(lab) == 1
    assert lab.specimen is None


def test_a_stray_reagent_in_the_input_is_ejected_to_inventory_not_flushed():
    lab = FakeLab(
        specimen_value=specimen(),
        input_stacks=[stack("alkaline_buffer", 4)],
        inventory={"cryo_solvent": 3},
        budget=40,
    )
    drive(lab)
    # 4 ejected back, 2 taken for the recipe, 2 left over in inventory after extraction.
    assert lab.inventory["alkaline_buffer"] == 2
    assert "input.eject" in lab.actions
    assert sample_count(lab) == 1


def test_a_sample_left_in_the_output_is_shipped_before_anything_else_starts():
    lab = FakeLab(output_stacks=[stack("gw_jaw_fang", 1)], budget=3)
    drive(lab)
    assert lab.actions[:2] == ["output.connect", "output.send"]
    assert sample_count(lab) == 1


def test_unneeded_loaded_reagents_are_unloaded_before_extract_can_destroy_them():
    lab = FakeLab(
        specimen_value=specimen(),
        loaded={"cryo_solvent": 9},
        inventory={"alkaline_buffer": 2, "cryo_solvent": 0},
        budget=40,
    )
    game, shop = drive(lab)
    assert lab.actions.index("unload_reagents") < lab.actions.index("extract")
    assert sample_count(lab) == 1
    # The 9 unloaded units went back to Inventory; the recipe then used 3 of them.
    assert lab.inventory["cryo_solvent"] == 6
    assert shop.purchases == []


def test_a_refused_ship_keeps_the_specimen_and_the_sample():
    lab = FakeLab(
        specimen_value=specimen(),
        output_stacks=[stack("gw_jaw_fang", 1)],
        budget=5,
    )
    lab.send_refusal = "target_full"
    game, shop = drive(lab)
    assert lab.specimen is not None
    assert lab.output_stacks != []
    assert ("output not shipped (target_full)", "warn") in game.statuses
    assert "discard" not in lab.actions


def test_a_refused_extract_is_a_warning_and_keeps_the_specimen():
    lab = FakeLab(
        specimen_value=specimen(), inventory={"alkaline_buffer": 2, "cryo_solvent": 3}, budget=12
    )
    lab.extract_refusal = "busy"
    game, shop = drive(lab)
    assert lab.specimen is not None
    assert "discard" not in lab.actions


def test_an_unanalyzable_specimen_is_discarded_with_a_warning():
    lab = FakeLab(specimen_value=specimen(stage="collected", recipe=None), budget=4)
    lab.analysis_refusal = "invalid_specimen"
    game, shop = drive(lab)
    assert lab.specimen is None
    assert ("specimen cannot be analyzed, discarded", "warn") in game.statuses


def test_a_missing_collector_is_a_warning_not_a_crash():
    lab = FakeLab(budget=3)
    game, shop = drive(lab, with_collector=False)
    assert ("bio_collector_1 not found", "warn") in game.statuses
    assert "take_from" not in lab.actions


def test_a_busy_take_from_retries_after_a_short_pause():
    lab = FakeLab(budget=4)
    lab.take_refusal = "busy"
    game, shop = drive(lab)
    # Two passes of (take_from, sleep): each sleep is the 5 s retry.
    assert game.clock.now == 10


def test_an_empty_collector_waits_without_a_warning():
    lab = FakeLab(collector_stock=0, budget=2)
    game, shop = drive(lab)
    assert not any(level == "warn" for _, level in game.statuses)


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
