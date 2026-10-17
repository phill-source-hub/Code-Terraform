"""Adapter tests: the scanner_1 script against a fake scanner and clock."""

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "scanner_1.py"


class _Stop(Exception):
    """Ends the scanner's endless loop after one sweep."""


class StopOnSleep(FakeGame):
    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        raise _Stop


def scanner_with(results, seconds=3600.0):
    """results: sector id -> ScanResult-like object. Records every scan call."""
    calls: list[str] = []
    owner = SimpleNamespace(
        scan=lambda sector: (
            calls.append(sector)
            or results.get(sector, SimpleNamespace(status="empty", message="", name=None))
        )
    )
    game = StopOnSleep()
    game.components["clock"] = FakeComponent(
        id="clock",
        type_id="clock",
        methods={"real_seconds_per_hour": lambda: seconds},
    )
    return owner, game, calls


def run(owner, game):
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )


def test_sweep_covers_base_and_its_neighbours_nearest_first():
    owner, game, calls = scanner_with({})
    run(owner, game)
    assert calls == ["E13", "D13", "E12", "E14", "F13"]


def test_prints_found_items_and_empty_sectors():
    results = {"E13": SimpleNamespace(status="ok", message="", name="Soil Sample")}
    owner, game, _ = scanner_with(results)
    run(owner, game)
    assert game.printed[0] == "E13: Soil Sample\n"
    assert game.printed[1] == "D13: empty\n"


def test_other_statuses_warn_and_the_sweep_goes_on():
    results = {"E13": SimpleNamespace(status="busy", message="busy", name=None)}
    owner, game, calls = scanner_with(results)
    run(owner, game)
    assert game.statuses[0] == ("E13 busy", "warn")
    assert len(calls) == 5


def test_waits_one_world_hour_between_sweeps():
    owner, game, _ = scanner_with({}, seconds=720.0)
    run(owner, game)
    assert game.clock.now == 720.0


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
