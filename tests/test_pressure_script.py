"""Adapter tests: the pressure_1 script against a fake generator that replays a sweep sequence.

Each pass reads the gauge first, then the window. The fake replays one (gauge, low, high) reading
per pass and ends the script when the readings run out.
"""

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "pressure_1.py"


class _Stop(Exception):
    """Ends the generator's loop when the readings are used up."""


def run(readings, sync_status="ok"):
    """readings: list of (gauge, window_low, window_high). Returns (syncs, game)."""
    queue = list(readings)
    current: dict = {}
    syncs: list[int] = []

    def gauge():
        if not queue:
            raise _Stop
        current["reading"] = queue.pop(0)
        return current["reading"][0]

    def sync():
        syncs.append(current["reading"][0])
        return SimpleNamespace(status=sync_status, message="")

    owner = SimpleNamespace(
        gauge=gauge,
        next_window_low=lambda: current["reading"][1],
        next_window_high=lambda: current["reading"][2],
        sync=sync,
        efficiency=lambda: 100.0,
    )
    game = FakeGame()
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    return syncs, game


def test_syncs_once_when_the_gauge_enters_the_window():
    # Window 40-60 on this sweep. Gauge 10 and 30 are outside, 45 and 50 inside.
    readings = [(10.0, 40.0, 60.0), (30.0, 40.0, 60.0), (45.0, 40.0, 60.0), (50.0, 40.0, 60.0)]
    syncs, _ = run(readings)
    assert syncs == [45.0]


def test_no_sync_when_the_gauge_never_enters_the_window():
    readings = [(10.0, 40.0, 60.0), (20.0, 40.0, 60.0), (30.0, 40.0, 60.0)]
    syncs, _ = run(readings)
    assert syncs == []


def test_window_edges_are_included():
    readings = [(40.0, 40.0, 60.0), (60.0, 40.0, 60.0)]
    syncs, _ = run(readings)
    # The first sync counts for the sweep; the gauge at 60 is the same sweep, so no second call.
    assert syncs == [40.0]


def test_syncs_again_on_the_next_sweep_when_the_window_moves():
    # Sweep 1 window 40-60, sweep 2 (the gauge wrapped to 5) window 20-30.
    readings = [
        (45.0, 40.0, 60.0),
        (90.0, 40.0, 60.0),
        (5.0, 20.0, 30.0),
        (25.0, 20.0, 30.0),
    ]
    syncs, _ = run(readings)
    assert syncs == [45.0, 25.0]


def test_window_is_read_each_pass_not_cached():
    # The window moves within the same run; a cached first window would miss the second sweep.
    readings = [
        (50.0, 40.0, 60.0),
        (2.0, 0.0, 5.0),
        (3.0, 0.0, 5.0),
    ]
    syncs, _ = run(readings)
    assert syncs == [50.0, 2.0]


def test_a_rejected_sync_is_printed_as_a_warning():
    readings = [(50.0, 40.0, 60.0)]
    _, game = run(readings, sync_status="busy")
    assert "warning: sync busy\n" in game.printed


def test_status_shows_gauge_window_and_efficiency_and_changes_only_when_it_changes():
    readings = [(50.0, 40.0, 60.0), (50.0, 40.0, 60.0), (55.0, 40.0, 60.0)]
    _, game = run(readings)
    assert game.statuses[0] == ("gauge 50.0 window 40.0-60.0 efficiency 100.0%", "info")
    assert len(game.statuses) == 2


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
