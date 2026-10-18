"""Adapter tests: the heater_1 script against a fake heater with a hidden optimum per thermal state.

The fake gives efficiency 100% at a state's optimum, 31% one step away and 10% further out, as the
manual describes. Each state is a day; `advance_on` lists the set_power call numbers after which the
day moves on, so a test can change the state mid-scan. The loop has no stop of its own, so the fake
ends it with _Stop once `max_calls` set_power calls have been made.
"""

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "heater_1.py"
SCAN = [i / 10 for i in range(1, 101)]


class _Stop(Exception):
    """Ends the heater's loop after the requested number of set_power calls."""


def run(
    optima,
    states,
    *,
    max_calls=40,
    advance_on=(),
    power_status="ok",
):
    """Run the script. states[i] is the thermal state of day i; optima maps a state to its peak.

    Returns (powers, game): every set_power argument in order, and the fake game.
    """
    game = FakeGame()
    day = {"index": 0, "power": 0.0}
    powers: list[float] = []

    def thermal_state():
        return states[day["index"]]

    def set_power(watts):
        if len(powers) >= max_calls:
            raise _Stop
        powers.append(watts)
        day["power"] = watts
        if len(powers) in advance_on:
            day["index"] += 1
        return SimpleNamespace(status=power_status, message="")

    def efficiency():
        power = day["power"]
        peak = optima.get(thermal_state())
        if power == 0 or peak is None:
            return 10.0 if power else 0.0
        if abs(power - peak) < 1e-9:
            return 100.0
        if abs(power - peak) <= 0.1 + 1e-9:
            return 31.0
        return 10.0

    owner = SimpleNamespace(
        set_power=set_power,
        thermal_state=thermal_state,
        efficiency=efficiency,
        output=lambda: 1.25,
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    return powers, game


def test_scans_upward_from_0_1_and_keeps_the_first_full_reading():
    powers, game = run({"clear": 3.0}, ["clear"], max_calls=31)
    assert powers[:30] == SCAN[:30]
    assert "best power for clear: 3.0\n" in game.printed


def test_scan_stops_at_the_first_full_reading():
    # Probes 0.1 to 3.0 (30 calls), then the held power 3.0 on the next pass. 3.1 is never tried.
    powers, _ = run({"clear": 3.0}, ["clear"], max_calls=31)
    assert powers == SCAN[:30] + [3.0]


def test_holds_the_found_power_on_every_later_pass():
    powers, _ = run({"clear": 3.0}, ["clear"], max_calls=35)
    assert powers[30:] == [3.0] * 5


def test_known_state_is_not_scanned_again():
    powers, _ = run({"clear": 3.0}, ["clear"], max_calls=60)
    assert powers.count(0.1) == 1


def test_a_new_day_with_a_new_state_scans_that_state():
    # Day 1 (clear, peak 3.0) is found at probe 30; call 31 holds 3.0 and then the day moves on.
    # Day 2 (dust_storm, peak 5.0) is scanned from 0.1 up to 5.0: 50 probes.
    optima = {"clear": 3.0, "dust_storm": 5.0}
    _, game = run(optima, ["clear", "dust_storm"], advance_on=(31,), max_calls=82)
    assert "best power for clear: 3.0\n" in game.printed
    assert "best power for dust_storm: 5.0\n" in game.printed


def test_a_known_state_returning_on_a_later_day_is_not_scanned_again():
    optima = {"clear": 3.0, "dust_storm": 5.0}
    powers, _ = run(
        optima,
        ["clear", "dust_storm", "clear"],
        advance_on=(31, 82),
        max_calls=90,
    )
    # Storm found at call 81 (powers[80]); call 82 holds 5.0 and the day moves to clear. Clear is
    # already known, so it holds 3.0 at once and 0.1 is not probed again.
    assert powers[81:] == [5.0] + [3.0] * 8
    assert powers.count(0.1) == 2


def test_day_change_mid_scan_discards_the_old_state_reading():
    # Day moves on after probe 2 (0.2), so the clear scan is abandoned and dust_storm is scanned.
    optima = {"clear": 3.0, "dust_storm": 5.0}
    _, game = run(optima, ["clear", "dust_storm"], advance_on=(2,), max_calls=60)
    assert not any("best power for clear" in line for line in game.printed)
    assert "best power for dust_storm: 5.0\n" in game.printed


def test_state_without_a_peak_warns_once_then_stays_off_without_rescanning():
    powers, game = run({}, ["clear"], max_calls=130)
    assert powers[:100] == SCAN
    assert powers[100:] == [0] * 30
    warnings = [line for line in game.printed if "no power reached 100%" in line]
    assert len(warnings) == 1


def test_rejected_probe_is_not_read_as_a_missing_peak():
    powers, game = run({"clear": 3.0}, ["clear"], max_calls=5, power_status="offline")
    assert not any("no power reached 100%" in line for line in game.printed)
    assert not any("best power" in line for line in game.printed)
    assert game.printed.count("warning: set_power offline\n") == 1


def test_rejected_probes_retry_on_the_next_pass():
    # Each pass starts the scan again from 0.1 while the fault lasts.
    powers, _ = run({"clear": 3.0}, ["clear"], max_calls=4, power_status="offline")
    assert powers == [0.1, 0.1, 0.1, 0.1]


def test_status_shows_state_power_efficiency_and_output():
    _, game = run({"clear": 3.0}, ["clear"], max_calls=31)
    assert game.statuses[-1] == ("state clear power 3.0 efficiency 100.0% output 1.25", "info")


def test_status_is_set_only_when_it_changes():
    _, game = run({"clear": 3.0}, ["clear"], max_calls=40)
    # One scanning status, then one settled status: the held power adds no new text.
    assert [message for message, _ in game.statuses].count(
        "state clear power 3.0 efficiency 100.0% output 1.25"
    ) == 1


def test_scan_pauses_one_second_per_probe_and_each_pass_pauses_one_second():
    # Pass 1: probe 0.1 (settle 1 s), found, pass pause 1 s. Passes 2 and 3 hold 0.1 with a pause
    # each. The fourth set_power raises, and that is read at the clock's 4 s.
    _, game = run({"clear": 0.1}, ["clear"], max_calls=3)
    assert game.clock.now == 4.0


def test_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
