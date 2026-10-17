"""Adapter tests: the scanner_1 script against a fake scanner, harvester position and clock."""

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "scanner_1.py"


class _Stop(Exception):
    """Ends the scanner's endless loop after a set number of scans."""


def scanner_script(
    limit, harvester_position="E13", results=None, with_harvester=True, seconds=3600.0
):
    """Build a fake game and self. Stops after `limit` scans (the scan call raises _Stop)."""
    results = results or {}
    game = FakeGame()
    game.components["clock"] = FakeComponent(
        id="clock",
        type_id="clock",
        methods={"real_seconds_per_hour": lambda: seconds},
    )
    if with_harvester:
        game.components["harvester_1"] = FakeComponent(
            id="harvester_1",
            type_id="harvester",
            methods={"get_position": lambda: harvester_position},
        )
    scans: list[str] = []

    def scan(name):
        scans.append(name)
        if len(scans) >= limit:
            raise _Stop
        return results.get(name, SimpleNamespace(status="empty", message="", name=None))

    owner = SimpleNamespace(scan=scan)
    return owner, game, scans


def run(owner, game):
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )


def test_first_scan_is_the_sector_the_harvester_stands_on():
    owner, game, scans = scanner_script(limit=1, harvester_position="H24")
    run(owner, game)
    assert scans == ["H24"]


def test_scans_outward_from_the_harvester_not_from_base():
    # Harvester far from base: the next sectors are near it, not near E13.
    owner, game, scans = scanner_script(limit=3, harvester_position="A1")
    run(owner, game)
    assert scans[0] == "A1"
    assert set(scans[1:]) == {"A2", "B1"}


def test_moves_centre_when_the_harvester_moves():
    game = FakeGame()
    positions = iter(["E13", "E14"])
    game.components["harvester_1"] = FakeComponent(
        id="harvester_1",
        type_id="harvester",
        methods={"get_position": lambda: next(positions, "E14")},
    )
    scans: list[str] = []

    def scan(name):
        scans.append(name)
        if len(scans) >= 2:
            raise _Stop
        return SimpleNamespace(status="empty", message="", name=None)

    owner = SimpleNamespace(scan=scan)
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 3600.0}
    )
    run(owner, game)
    assert scans == ["E13", "E14"]


def test_falls_back_to_base_when_no_harvester():
    owner, game, scans = scanner_script(limit=1, with_harvester=False)
    run(owner, game)
    assert scans == ["E13"]


def test_prints_found_items_and_empty_sectors():
    results = {"E13": SimpleNamespace(status="ok", message="", name="Soil Sample")}
    owner, game, _ = scanner_script(limit=3, results=results)
    run(owner, game)
    # Ties break by row first, so D13 comes before E12.
    assert game.printed == ["E13: Soil Sample\n", "D13: empty\n"]


def test_other_statuses_warn():
    results = {"E13": SimpleNamespace(status="busy", message="busy", name=None)}
    owner, game, _ = scanner_script(limit=2, results=results)
    run(owner, game)
    assert ("E13 busy", "warn") in game.statuses


def test_progress_is_reported_in_status():
    owner, game, _ = scanner_script(limit=3)
    run(owner, game)
    assert game.statuses[-1] == ("2 of 192 scanned, centre E13", "info")


def test_a_finished_grid_restarts_after_one_world_hour():
    # Stop on the sleep that ends the full sweep. Make the sweep tiny by pre-filling scanned.
    scans: list[str] = []
    owner = SimpleNamespace(
        scan=lambda name: (
            scans.append(name) or SimpleNamespace(status="empty", message="", name=None)
        )
    )
    source = SCRIPT.read_text(encoding="utf-8")
    # Shrink the grid to 1 sector so one scan finishes it; the sleep then stops the loop.
    source = source.replace("ROWS = 8", "ROWS = 1").replace("COLS = 24", "COLS = 1")
    source = source.replace("BASE_ROW = 4", "BASE_ROW = 0").replace("BASE_COL = 12", "BASE_COL = 0")

    class StopAtSleep(FakeGame):
        def sleep(self, seconds, /):
            super().sleep(seconds)
            raise _Stop

    game = StopAtSleep()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 720.0}
    )
    with suppress(_Stop):
        run_script(source, game, filename=str(SCRIPT), extra_globals={"self": owner})
    assert scans == ["A1"]
    assert game.clock.now == 720.0


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
