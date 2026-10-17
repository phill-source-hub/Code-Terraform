"""Adapter tests: the o2gen_1 script against a fake generator and atmosphere.

The loop has no sleep, so each test stops it after a fixed number of passes (set_intake raises).
"""

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "o2gen_1.py"


class _Stop(Exception):
    """Ends the generator's loop after the requested number of passes."""


def run(
    waste_values,
    co2=800.0,
    passes=None,
    dump_status="ok",
    dump_penalty=0.0,
    intake_status="ok",
    atmosphere=True,
):
    """Run the script. waste_values is a list read once per pass (the last value repeats)."""
    passes = passes or len(waste_values)
    intakes: list[float] = []
    dumps: list[int] = []
    waste_iter = iter(waste_values)
    current = {"waste": waste_values[0]}

    def read_waste():
        with suppress(StopIteration):
            current["waste"] = next(waste_iter)
        return current["waste"]

    def set_intake(value):
        # Stop at the start of pass passes+1, so pass `passes` runs to its end.
        if len(intakes) >= passes:
            raise _Stop
        intakes.append(value)
        return SimpleNamespace(status=intake_status, message="")

    def dump_waste():
        dumps.append(1)
        return SimpleNamespace(status=dump_status, message="", penalty=dump_penalty)

    owner = SimpleNamespace(
        set_intake=set_intake,
        waste=read_waste,
        dump_waste=dump_waste,
        dump_penalty=lambda: dump_penalty,
        efficiency=lambda: 100.0,
    )
    game = FakeGame()
    if atmosphere:
        game.components["atmosphere"] = FakeComponent(
            id="atmosphere", type_id="atmosphere", methods={"get_co2": lambda: co2}
        )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    return game, intakes, dumps


def test_intake_is_exactly_one_tenth_of_co2_unrounded():
    _, intakes, _ = run([10.0], co2=803.7, passes=1)
    assert intakes == [80.37]


def test_intake_tracks_changing_co2_each_pass():
    _, intakes, _ = run([10.0, 10.0], co2=800.0, passes=2)
    assert intakes == [80.0, 80.0]


def test_dumps_inside_the_window_at_both_edges():
    game, _, dumps = run([50.0, 60.0, 55.0], passes=3)
    assert len(dumps) == 3
    assert "dumped waste at 50.0, penalty 0.0\n" in game.printed


def test_never_dumps_below_the_window():
    _, _, dumps = run([49.9, 0.0, 30.0], passes=3)
    assert dumps == []


def test_never_dumps_above_the_window_and_warns_once():
    game, _, dumps = run([61.0, 75.0, 85.0], passes=3)
    assert dumps == []
    warnings = [line for line in game.printed if "is above 60" in line]
    assert len(warnings) == 1


def test_warning_clears_when_waste_returns_to_the_window_and_repeats_on_a_new_excursion():
    game, _, dumps = run([61.0, 40.0, 61.0], passes=3)
    warnings = [line for line in game.printed if "is above 60" in line]
    assert len(warnings) == 2


def test_a_dump_that_reports_a_penalty_is_warned_about():
    game, _, _ = run([55.0], dump_penalty=0.25, passes=1)
    assert "warning: dump at 55.0 reported a penalty\n" in game.printed


def test_rejected_intake_is_printed_as_a_warning():
    game, _, _ = run([10.0], intake_status="offline", passes=1)
    assert "warning: set_intake offline\n" in game.printed


def test_rejected_dump_is_printed_as_a_warning():
    game, _, _ = run([55.0], dump_status="busy", passes=1)
    assert "warning: dump busy\n" in game.printed


def test_status_shows_intake_waste_efficiency_and_penalty():
    game, _, _ = run([30.0], co2=800.0, passes=1)
    assert game.statuses[-1] == ("intake 80.0 waste 30.0 eff 100.0% penalty 0.0", "info")


def test_status_is_set_only_when_it_changes():
    game, _, _ = run([30.0, 30.0, 30.0], passes=3)
    assert len(game.statuses) == 1


class StopOnStatus(FakeGame):
    """The missing-atmosphere branch only sets a status, so its first status ends the test."""

    def set_status(self, message, level="info"):
        super().set_status(message, level)
        raise _Stop


def test_missing_atmosphere_is_an_error_status():
    game = StopOnStatus()
    owner = SimpleNamespace(set_intake=lambda value: None, waste=lambda: 30.0)
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    assert game.statuses == [("atmosphere not found", "error")]


def test_loop_has_no_sleep():
    # Continuous running: no sleep means the fake clock never advances.
    game, _, _ = run([10.0, 10.0, 10.0], passes=3)
    assert game.clock.now == 0.0


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line


def test_last_resort_dump_takes_the_penalty_at_ninety():
    game, _, dumps = run([92.0], passes=1)
    assert len(dumps) == 1
    assert "LAST RESORT dump at 92.0, penalty 0.0\n" in game.printed


def test_no_last_resort_dump_below_ninety():
    game, _, dumps = run([89.0], passes=1)
    assert dumps == []
    assert any("is above 60" in line for line in game.printed)
