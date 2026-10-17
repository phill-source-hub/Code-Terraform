"""Adapter test: run the real solar_1 script against a fake Solar Generator and Clock."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.libs.solar_tracker import target_tilt
from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "solar_1.py"


class _Stop(Exception):
    """Ends the script's endless loop after a set number of samples."""


class StoppingGame(FakeGame):
    def __init__(self, samples: int, **kwargs):
        super().__init__(**kwargs)
        self.samples_left = samples
        self.sleeps: list[float] = []

    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        self.sleeps.append(seconds)
        self.samples_left -= 1
        if self.samples_left <= 0:
            raise _Stop


def _game(elevation, samples, tilts, set_status_result=None):
    game = StoppingGame(samples=samples)
    game.components["clock"] = FakeComponent(
        id="clock",
        type_id="clock",
        methods={
            "get_elevation": lambda: elevation,
            "real_seconds_per_hour": lambda: 3600.0,
        },
    )
    panel = SimpleNamespace(
        set_tilt=lambda tilt: (
            tilts.append(tilt) or set_status_result or SimpleNamespace(status="ok", message="")
        )
    )
    return game, panel


def _run(game, panel):
    with pytest.raises(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": panel},
        )


def test_tilt_follows_sun_elevation():
    tilts: list[float] = []
    game, panel = _game(elevation=60.0, samples=1, tilts=tilts)
    _run(game, panel)
    assert tilts == [30.0]
    assert game.statuses[-1] == ("tilt 30.0 deg", "info")


def test_night_sets_rest_tilt():
    tilts: list[float] = []
    game, panel = _game(elevation=0.0, samples=1, tilts=tilts)
    _run(game, panel)
    assert tilts == [90.0]


def test_samples_every_sixtieth_of_a_world_hour():
    tilts: list[float] = []
    game, panel = _game(elevation=45.0, samples=3, tilts=tilts)
    _run(game, panel)
    assert game.sleeps == [60.0, 60.0, 60.0]
    assert len(tilts) == 3


def test_tracks_a_moving_sun():
    tilts: list[float] = []
    game, panel = _game(elevation=20.0, samples=1, tilts=tilts)
    _run(game, panel)
    assert tilts[-1] == target_tilt(20.0) == 70.0


def test_rejected_tilt_write_is_reported_as_error():
    tilts: list[float] = []
    game, panel = _game(
        elevation=30.0,
        samples=1,
        tilts=tilts,
        set_status_result=SimpleNamespace(status="busy", message="busy"),
    )
    _run(game, panel)
    assert game.statuses[-1] == ("set_tilt busy", "error")


def test_missing_clock_reports_error_and_exits(monkeypatch):
    game = FakeGame()
    panel = SimpleNamespace(set_tilt=lambda tilt: SimpleNamespace(status="ok", message=""))
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": panel},
    )
    assert game.statuses == [("clock not found", "error")]
