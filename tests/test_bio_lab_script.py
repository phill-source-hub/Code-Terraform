"""Adapter tests: the Bio Lab script against a fake lab, input port, output port and collector.

The loop has no stop of its own, so each test ends it at the first sleep (a blocked path) or at
a call it is checking. The output port keeps items between calls, as the game's does.
"""

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "bio_lab_1.py"


class _Stop(Exception):
    """Ends the lab's loop at the call under test."""


class StopOnSleep(FakeGame):
    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        raise _Stop


def ok(**extra):
    return SimpleNamespace(status="ok", message="", **extra)


def lab(specimen=None, loaded=None, send_status="ok", extract_status="ok", staged=None):
    """Returns (lab, record, output_items). output_items is the port's live contents."""
    record: list = []
    output_items: list = []
    input_items: list = list(staged or [])

    def connect(target):
        record.append(("output.connect", target))
        return ok()

    def send(item, qty, props, mode):
        if send_status != "ok":
            record.append(("output.send", item, "refused", send_status))
            return SimpleNamespace(status=send_status, message="")
        record.append(("output.send", item, qty, props, mode))
        output_items.clear()
        return ok()

    def extract():
        record.append(("extract",))
        if extract_status == "ok":
            output_items.append(SimpleNamespace(id="sample_x", count=1, properties={"glow": 3}))
        return SimpleNamespace(status=extract_status, message="")

    owner = SimpleNamespace(
        specimen=specimen,
        loaded_reagents=loaded or {},
        take_from=lambda collector: record.append(("take_from",)) or ok(),
        analyze=lambda: record.append(("analyze",)) or ok(info=None),
        load=lambda item, qty: record.append(("load", item, qty)) or ok(),
        extract=extract,
        discard=lambda: record.append(("discard",)) or ok(),
        input=SimpleNamespace(
            connect=lambda target: record.append(("input.connect", target)) or ok(),
            take=lambda item, qty: record.append(("input.take", item, qty)) or ok(moved=qty),
            stacks=lambda: list(input_items),
            eject=lambda dest, item, qty, props, mode: (
                record.append(("input.eject", item, qty)) or input_items.clear() or ok()
            ),
        ),
        output=SimpleNamespace(
            connect=connect,
            send=send,
            stacks=lambda: list(output_items),
        ),
    )
    return owner, record, output_items


def run(owner, collector=True):
    game = StopOnSleep()
    if collector:
        game.components["bio_collector_1"] = FakeComponent(
            id="bio_collector_1", type_id="bio_collector"
        )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    return game


def _raise_stop():
    raise _Stop


def stop_when(record, name):
    """Make the named call stop the loop after recording it."""

    def fake(*args):
        record.append((name,))
        raise _Stop

    return fake


def test_takes_specimen_from_collector_when_chamber_is_empty():
    owner, record, _ = lab(specimen=None)
    owner.take_from = stop_when(record, "take_from")
    run(owner)
    assert record == [("take_from",)]


def test_analyzes_a_collected_specimen():
    owner, record, _ = lab(specimen=SimpleNamespace(stage="collected", recipe=None))
    owner.analyze = stop_when(record, "analyze")
    run(owner)
    assert record == [("analyze",)]


def test_stages_missing_reagent_from_inventory_then_loads_it():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 4})
    owner, record, _ = lab(specimen=specimen, loaded={})
    owner.load = stop_when(record, "load")
    run(owner)
    assert ("input.connect", "inventory") in record
    assert ("input.take", "alkaline_buffer", 4) in record


def test_extracts_once_recipe_is_loaded_and_leaves_the_sample_in_output():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 2})
    owner, record, output_items = lab(specimen=specimen, loaded={"alkaline_buffer": 2})
    owner.extract = stop_when(record, "extract")
    run(owner)
    assert record == [("extract",)]


def test_ships_the_output_then_discards_the_specimen():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 2})
    owner, record, output_items = lab(specimen=specimen, loaded={"alkaline_buffer": 2})
    output_items.append(SimpleNamespace(id="sample_x", count=1, properties={"glow": 3}))
    owner.discard = stop_when(record, "discard")
    run(owner)
    names = [entry[0] for entry in record]
    assert names.index("output.connect") < names.index("output.send") < names.index("discard")
    assert ("output.send", "sample_x", 1, {"glow": 3}, "exact") in record
    assert output_items == []


def test_output_holding_items_blocks_extraction_and_restocking():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 4})
    owner, record, output_items = lab(specimen=specimen, loaded={})
    output_items.append(SimpleNamespace(id="sample_x", count=1, properties=None))
    owner.discard = stop_when(record, "discard")
    run(owner)
    assert ("extract",) not in record
    assert ("input.take", "alkaline_buffer", 4) not in record


def test_refused_send_keeps_the_specimen_and_warns():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 2})
    owner, record, output_items = lab(
        specimen=specimen, loaded={"alkaline_buffer": 2}, send_status="research_required"
    )
    output_items.append(SimpleNamespace(id="sample_x", count=1, properties=None))
    game = run(owner)
    assert ("discard",) not in record
    assert output_items != []
    assert game.statuses[-1] == ("output not shipped (research_required), specimen kept", "warn")
    assert "warning: output not shipped (research_required), specimen kept\n" in game.printed


def test_extract_failure_is_a_warning_and_keeps_the_specimen():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 2})
    owner, record, _ = lab(
        specimen=specimen, loaded={"alkaline_buffer": 2}, extract_status="recipe_mismatch"
    )
    game = run(owner)
    assert game.statuses[-1] == ("extract recipe_mismatch", "warn")
    assert ("discard",) not in record


def test_missing_collector_is_an_error():
    owner, record, _ = lab(specimen=None)
    game = run(owner, collector=False)
    assert game.statuses[-1] == ("bio_collector_1 not found", "error")
    assert record == []


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line


def test_a_different_reagent_in_the_input_is_ejected_before_taking_the_next():
    specimen = SimpleNamespace(stage="analyzed", recipe={"cryo_solvent": 3})
    stray = SimpleNamespace(id="alkaline_buffer", count=2, properties=None)
    owner, record, _ = lab(specimen=specimen, loaded={}, staged=[stray])
    owner.load = stop_when(record, "load")
    run(owner)
    names = [entry[0] for entry in record]
    assert ("input.eject", "alkaline_buffer", 2) in record
    assert names.index("input.eject") < names.index("input.take")


def test_loads_only_what_the_take_actually_moved():
    specimen = SimpleNamespace(stage="analyzed", recipe={"cryo_solvent": 6})
    owner, record, _ = lab(specimen=specimen, loaded={})
    owner.input.take = lambda item, qty: record.append(("input.take", item, qty)) or ok(moved=2)
    owner.load = lambda item, qty: record.append(("load", item, qty)) or _raise_stop()
    run(owner)
    assert ("load", "cryo_solvent", 2) in record


def test_a_failed_take_from_the_collector_is_printed_as_a_warning():
    owner, record, _ = lab(specimen=None)
    owner.take_from = lambda collector: SimpleNamespace(status="source_busy", message="")
    game = run(owner)
    assert "warning: take_from source_busy\n" in game.printed


def test_discard_input_empty_is_not_a_warning():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 2})
    owner, record, output_items = lab(specimen=specimen, loaded={"alkaline_buffer": 2})
    output_items.append(SimpleNamespace(id="sample_x", count=1, properties=None))
    owner.discard = lambda: (
        record.append(("discard",)) or SimpleNamespace(status="input_empty", message="")
    )
    owner.extract = lambda: record.append(("extract",)) or _raise_stop()
    game = run(owner)
    assert ("discard",) in record
    assert not any(line.startswith("warning: discard") for line in game.printed)
