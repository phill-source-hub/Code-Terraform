"""Adapter tests: the Bio Lab script against a fake lab, input and output ports, and collector."""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent
from tests.harness.loop import StopOnSleep, run_loop, stop_after

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "bio_lab_1.py"


def ok(**extra):
    return SimpleNamespace(status="ok", message="", **extra)


def lab(specimen=None, loaded=None, record=None):
    record = record if record is not None else []
    port = lambda name: SimpleNamespace(  # noqa: E731
        connect=lambda target: record.append((name + ".connect", target)) or ok(),
        take=lambda item, qty: record.append((name + ".take", item, qty)) or ok(),
        send=lambda item, qty, props, mode: (
            record.append((name + ".send", item, qty, props, mode)) or ok()
        ),
        stacks=lambda: [SimpleNamespace(id="sample_x", count=1, properties={"glow": 3})],
    )
    owner = SimpleNamespace(
        specimen=specimen,
        loaded_reagents=loaded or {},
        take_from=lambda collector: record.append(("take_from",)) or ok(),
        analyze=lambda: record.append(("analyze",)) or ok(info=None),
        load=lambda item, qty: record.append(("load", item, qty)) or ok(),
        extract=lambda: record.append(("extract",)) or ok(),
        discard=lambda: record.append(("discard",)) or ok(),
        input=port("input"),
        output=port("output"),
    )
    return owner, record


def run(owner, collector=True):
    game = StopOnSleep()
    if collector:
        game.components["bio_collector_1"] = FakeComponent(
            id="bio_collector_1", type_id="bio_collector"
        )
    run_loop(SCRIPT, game, owner)
    return game


def test_takes_specimen_from_collector_when_chamber_is_empty():
    owner, record = lab(specimen=None)
    owner.take_from = stop_after(record, name="take_from")
    run(owner)
    assert record[0][0] == "take_from"


def test_analyzes_a_collected_specimen():
    owner, record = lab(specimen=SimpleNamespace(stage="collected", recipe=None))
    owner.analyze = stop_after(record, name="analyze")
    run(owner)
    assert record[0][0] == "analyze"


def test_stages_missing_reagent_from_inventory_then_loads_it():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 4})
    owner, record = lab(specimen=specimen, loaded={})
    owner.load = stop_after(record, name="load")
    run(owner)
    assert ("input.connect", "inventory") in record
    assert ("input.take", "alkaline_buffer", 4) in record
    assert record[-1][0] == "load" or ("load", "alkaline_buffer", 4) in record


def test_extracts_once_recipe_is_fully_loaded_then_ships_and_discards():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 2})
    owner, record = lab(specimen=specimen, loaded={"alkaline_buffer": 2})
    owner.discard = stop_after(record, name="discard")
    run(owner)
    names = [entry[0] for entry in record]
    assert names.index("extract") < names.index("output.connect") < names.index("output.send")
    assert names[-1] == "discard"
    assert ("output.send", "sample_x", 1, {"glow": 3}, "exact") in record


def test_extract_failure_is_a_warning_and_keeps_the_specimen():
    specimen = SimpleNamespace(stage="analyzed", recipe={"alkaline_buffer": 2})
    owner, record = lab(specimen=specimen, loaded={"alkaline_buffer": 2})
    owner.extract = lambda: (
        record.append(("extract",)) or SimpleNamespace(status="recipe_mismatch", message="")
    )
    game = run(owner)
    assert game.statuses[-1] == ("extract recipe_mismatch", "warn")
    assert all(entry[0] != "discard" for entry in record)


def test_missing_collector_is_an_error():
    owner, record = lab(specimen=None)
    game = run(owner, collector=False)
    assert game.statuses[-1] == ("bio_collector_1 not found", "error")
    assert record == []


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
