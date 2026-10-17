"""Adapter tests: the scanner_1 snake scan against a fake scanner, Data Archive and clock."""

import json
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "scanner_1.py"


class _Stop(Exception):
    """Ends the scanner's endless loop."""


class StopOnSleep(FakeGame):
    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        raise _Stop


def _notebook(saves: list):
    def set_value(key, value):
        # The Data Archive stores a copy and requires JSON-safe values (manual: Value rules).
        saves.append((key, json.loads(json.dumps(value))))
        return SimpleNamespace(status="ok", message="")

    return FakeComponent(id="notebook", type_id="notebook", methods={"set": set_value})


def run_grid(results=None, notebook=True, seconds=3600.0, source_override=None):
    """Run one full pass of the scanner. Returns (scans, saves, game)."""
    results = results or {}
    scans: list[str] = []
    saves: list = []
    game = StopOnSleep()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: seconds}
    )
    if notebook:
        game.components["notebook"] = _notebook(saves)

    def scan(name):
        scans.append(name)
        return results.get(name, SimpleNamespace(status="empty", message="", name=None, value=None))

    owner = SimpleNamespace(scan=scan)
    source = SCRIPT.read_text(encoding="utf-8")
    if source_override:
        source = source_override(source)
    with suppress(_Stop):
        run_script(source, game, filename=str(SCRIPT), extra_globals={"self": owner})
    return scans, saves, game


def test_first_row_runs_left_to_right_then_second_row_right_to_left():
    scans, _, _ = run_grid()
    assert scans[:3] == ["A1", "A2", "A3"]
    assert scans[23] == "A24"
    assert scans[24] == "B24"
    assert scans[25] == "B23"


def test_every_sector_is_scanned_exactly_once_in_one_pass():
    scans, _, _ = run_grid()
    assert len(scans) == 192
    assert len(set(scans)) == 192


def test_map_is_saved_at_the_end_of_each_row():
    _, saves, _ = run_grid()
    assert len(saves) == 8
    assert all(key == "scanner.map" for key, _ in saves)
    assert len(saves[0][1]) == 24
    assert len(saves[-1][1]) == 192


def test_map_entries_hold_status_name_and_value():
    results = {"E13": SimpleNamespace(status="ok", message="", name="Soil Sample", value=50)}
    _, saves, _ = run_grid(results=results)
    final = saves[-1][1]
    assert final["E13"] == {"status": "ok", "name": "Soil Sample", "value": 50}
    assert final["A1"] == {"status": "empty", "name": None, "value": None}


def test_prints_found_items_only():
    results = {"C5": SimpleNamespace(status="ok", message="", name="Crystal Shard", value=200)}
    _, _, game = run_grid(results=results)
    assert game.printed == ["C5: Crystal Shard\n"]


def test_other_statuses_warn_and_the_scan_goes_on():
    results = {"A2": SimpleNamespace(status="busy", message="busy", name=None, value=None)}
    scans, _, game = run_grid(results=results)
    assert ("A2 busy", "warn") in game.statuses
    assert len(scans) == 192


def test_without_data_archive_the_scan_still_runs():
    scans, saves, game = run_grid(notebook=False)
    assert len(scans) == 192
    assert saves == []
    assert game.statuses[-1] == ("map of 192 sectors saved", "info")


def test_failed_save_is_a_warning_not_a_stop():
    game = StopOnSleep()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 3600.0}
    )
    game.components["notebook"] = FakeComponent(
        id="notebook",
        type_id="notebook",
        methods={"set": lambda key, value: SimpleNamespace(status="invalid_key", message="bad")},
    )
    scans: list[str] = []
    owner = SimpleNamespace(
        scan=lambda name: (
            scans.append(name) or SimpleNamespace(status="empty", message="", name=None, value=None)
        )
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    assert ("map save invalid_key: bad", "warn") in game.statuses
    assert len(scans) == 192


def test_repeats_after_one_world_hour():
    _, _, game = run_grid(seconds=720.0)
    assert game.clock.now == 720.0
