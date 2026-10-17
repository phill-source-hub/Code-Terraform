"""Solar tracker: keep the panel facing the sun. Writes tilt.

Where it runs: machine script slot `solar_1` (Solar Generator, component id solar_1).
Self-contained on purpose: no imports (ADR-013, ADR-014). The rule is a copy of
    scripts/libs/solar_tracker.py. Tests check the copy gives the same tilt.
Rule: tilt = 90 - sun elevation (clamped 0-90). Night (elevation 0) rests at 90.
Timing: runs forever (the loop is what keeps the panel tracking). Samples every 1/60 of a
    world-clock hour, about 1 world minute, so the sun moves about 0.25 degrees between samples.
API facts relied on (docs/game/power.md, Clock): get_component("clock"), clock.get_elevation(),
    clock.real_seconds_per_hour(); self.set_tilt (self-only, status "ok"); set_status; sleep.
Failure: a missing clock or a rejected tilt write shows as an error in the status bar, and the
    loop keeps going. The panel resets to 90 when this script stops, so stopping is safe.
"""

TILT_MIN = 0.0
TILT_MAX = 90.0
SAMPLES_PER_WORLD_HOUR = 60


def clamp_tilt(tilt):
    return min(max(tilt, TILT_MIN), TILT_MAX)


def target_tilt(elevation):
    return clamp_tilt(TILT_MAX - elevation)


clock = get_component("clock")
if clock is None:
    set_status("clock not found", "error")
else:
    period = clock.real_seconds_per_hour() / SAMPLES_PER_WORLD_HOUR
    while True:
        try:
            tilt = target_tilt(clock.get_elevation())
            result = self.set_tilt(tilt)
            if result.status != "ok":
                set_status("set_tilt " + result.status, "error")
            else:
                set_status("tilt " + str(round(tilt, 1)) + " deg", "info")
        except (TypeError, ValueError) as error:
            set_status(str(error), "error")
        sleep(period)
