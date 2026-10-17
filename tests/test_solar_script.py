"""Adapter test: run the real solar_1 script against a fake Solar Generator."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.harness.fake_game import FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "solar_1.py"


class _Stop(Exception):
    """Ends the script's endless loop after one sweep."""


class OneSweepGame(FakeGame):
    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        if seconds >= 300:  # the sweep period: the script is about to repeat, so stop
            raise _Stop


def _panel(output_for):
    tilts: list[float] = []
    panel = SimpleNamespace(
        set_tilt=lambda tilt: tilts.append(tilt) or SimpleNamespace(status="ok", message=""),
        get_output=lambda: output_for(tilts[-1]),
    )
    return panel, tilts


@pytest.fixture
def script_source():
    return SCRIPT.read_text(encoding="utf-8")


def test_settles_on_peak_tilt_and_reports_it(script_source):
    panel, tilts = _panel(lambda tilt: 1000.0 - abs(tilt - 37.0) * 10.0)
    game = OneSweepGame()
    with pytest.raises(_Stop):
        run_script(script_source, game, filename=str(SCRIPT), extra_globals={"self": panel})
    assert tilts[-1] == 37.0
    assert game.statuses[-1] == ("tilt 37.0 deg", "info")


def test_night_sets_rest_tilt(script_source):
    panel, tilts = _panel(lambda tilt: 0.0)
    game = OneSweepGame()
    with pytest.raises(_Stop):
        run_script(script_source, game, filename=str(SCRIPT), extra_globals={"self": panel})
    assert tilts[-1] == 90.0


def test_rejected_tilt_write_is_reported_as_error(script_source):
    panel = SimpleNamespace(
        set_tilt=lambda tilt: SimpleNamespace(status="busy", message="busy"),
        get_output=lambda: 0.0,
    )
    game = OneSweepGame()
    with pytest.raises(_Stop):
        run_script(script_source, game, filename=str(SCRIPT), extra_globals={"self": panel})
    assert game.statuses[-1][1] == "error"


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line


def test_script_search_matches_library_on_a_known_peak(script_source):
    # Parity check: the inlined search and the tested library agree on the same output curve.
    from scripts.libs.solar_tracker import choose_tilt

    def curve(tilt):
        return 1000.0 - abs(tilt - 52.0) * 10.0

    panel, tilts = _panel(curve)
    game = OneSweepGame()
    with pytest.raises(_Stop):
        run_script(script_source, game, filename=str(SCRIPT), extra_globals={"self": panel})
    assert tilts[-1] == choose_tilt(curve) == 52.0
