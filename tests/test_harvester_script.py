"""Adapter tests: the harvester_1 script against a fake harvester, scanner snapshot and clock."""

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "harvester_1.py"


class _Stop(Exception):
    """Ends the harvester's endless loop at the call under test."""


class StopOnSleep(FakeGame):
    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        raise _Stop


def ok_item(name="Soil Sample"):
    return SimpleNamespace(status="ok", message="", id="soil_sample", name=name, value=50)


def harvester(
    heat=0,
    move_status="ok",
    collect_status="ok",
    store_status="ok",
    record=None,
    position="E13",
    held="",
):
    record = record if record is not None else []
    return SimpleNamespace(
        get_heat=lambda: heat,
        get_position=lambda: position,
        get_held=lambda: held,
        move=lambda sector: (
            record.append(("move", sector)) or SimpleNamespace(status=move_status, message="")
        ),
        collect=lambda: (
            record.append(("collect",)) or SimpleNamespace(status=collect_status, message="")
        ),
        store=lambda: (
            record.append(("store",))
            or SimpleNamespace(status=store_status, message="", item_id="soil_sample")
        ),
    ), record


def run(owner, snapshot, game=None, scanner=True):
    game = game or StopOnSleep()
    if scanner:
        game.components["scanner_1"] = FakeComponent(
            id="scanner_1",
            type_id="scanner",
            methods={"get_scanned": lambda: snapshot},
        )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    return game


def stop_on(record, name, status="ok"):
    def fake(*args):
        record.append((name,))
        raise _Stop

    return fake


def _stop_now():
    raise _Stop


def test_moves_one_cell_east_toward_an_item_in_the_same_row():
    owner, record = harvester()
    owner.move = lambda sector: record.append(sector) or _stop_now()
    run(owner, {"E14": ok_item()})
    assert record == ["E14"]


def test_picks_the_nearest_item_not_the_first_listed():
    owner, record = harvester()
    owner.move = lambda sector: record.append(sector) or _stop_now()
    run(owner, {"H24": ok_item(), "E14": ok_item()})
    assert record == ["E14"]


def test_collects_then_stores_when_standing_on_the_item():
    owner, record = harvester()
    owner.store = lambda: record.append(("store",)) or _stop_now()
    game = run(owner, {"E13": ok_item()})
    assert record == [("collect",), ("store",)]
    assert game.printed == []


def test_marks_empty_cells_done_and_does_not_store():
    # Only item is the cell the harvester stands on, and it is empty: collect, do not store, sleep.
    owner, record = harvester(collect_status="empty")
    game = run(owner, {"E13": ok_item()})
    assert ("store",) not in record
    assert game.statuses[-1] == ("no items to collect", "info")


def test_held_item_is_stored_before_anything_else():
    owner, record = harvester(held="soil_sample")
    owner.store = lambda: record.append(("store",)) or _stop_now()
    run(owner, {"E14": ok_item()})
    assert record == [("store",)]


def test_starts_from_the_position_the_game_reports_not_e13():
    owner, record = harvester(position="H24")
    owner.move = lambda sector: record.append(sector) or _stop_now()
    run(owner, {"H23": ok_item()})
    assert record == ["H23"]


def test_hot_harvester_cools_and_does_not_move():
    owner, record = harvester(heat=85)
    owner.move = lambda sector: record.append(sector)
    game = run(owner, {"E14": ok_item()})
    assert record == []
    assert game.statuses[-1] == ("cooling", "warn")


def test_refused_move_drops_target_and_warns():
    owner, record = harvester(move_status="too_far")
    owner.move = lambda sector: (
        record.append(sector) or SimpleNamespace(status="too_far", message="")
    )
    game = run(owner, {"E14": ok_item()})
    assert record == ["E14"]
    assert game.statuses[-1] == ("move too_far to E14", "warn")


def test_no_items_reports_status_and_waits():
    owner, record = harvester()
    game = run(owner, {})
    assert record == []
    assert game.statuses[-1] == ("no items to collect", "info")


def test_missing_scanner_is_an_error():
    owner, record = harvester()
    game = run(owner, {}, scanner=False)
    assert game.statuses[-1] == ("scanner_1 not found", "error")


def test_full_inventory_warns_and_keeps_item_held():
    owner, record = harvester(store_status="inventory_full")
    game = run(owner, {"E13": ok_item()})
    assert game.statuses[-1] == ("store inventory_full", "warn")


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
