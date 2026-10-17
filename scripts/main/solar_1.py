"""Solar tracker: keep the panel at the tilt that gives the most output. Writes tilt.

Where it runs: machine script slot `solar_1` (Solar Generator, component id solar_1).
Self-contained on purpose: no imports (ADR-013). The search is a copy of
    scripts/libs/solar_tracker.py. Tests check the copy behaves the same on the same inputs.
Inputs: none. Re-searches every SWEEP_PERIOD seconds of game time.
Assumptions: set_tilt is self-only and returns status "ok" (VERIFIED docs). The tilt resets to
    90 when this script stops, so stopping is safe. Settle time after a tilt change is a
    judgement (UNVERIFIED): output may need a moment to update.
API facts relied on (docs/game/power.md): self.set_tilt, self.get_output, set_status, sleep.
Failure: a rejected tilt write is shown in the status bar as an error and the loop retries.
"""

TILT_MIN = 0.0
TILT_MAX = 90.0
REST_TILT = 90.0
COARSE_STEP = 5.0
FINE_STEP = 1.0


def clamp_tilt(tilt: float) -> float:
    """Keep a tilt inside the panel's 0-90 degree range."""
    return min(max(tilt, TILT_MIN), TILT_MAX)


def scan(sample, low: float, high: float, step: float) -> tuple[float, float]:
    """Best (tilt, watts) over low..high inclusive, stepping by `step`. Ties keep the first."""
    count = round((high - low) / step)
    best_tilt = clamp_tilt(low)
    best_watts = sample(best_tilt)
    for index in range(1, count + 1):
        tilt = clamp_tilt(low + index * step)
        watts = sample(tilt)
        if watts > best_watts:
            best_tilt, best_watts = tilt, watts
    return best_tilt, best_watts


def choose_tilt(sample) -> float:
    """Tilt that gives the most output right now. Returns REST_TILT when nothing produces power."""
    coarse_tilt, coarse_watts = scan(sample, TILT_MIN, TILT_MAX, COARSE_STEP)
    if coarse_watts <= 0:
        return REST_TILT
    low = clamp_tilt(coarse_tilt - COARSE_STEP)
    high = clamp_tilt(coarse_tilt + COARSE_STEP)
    fine_tilt, _ = scan(sample, low, high, FINE_STEP)
    return fine_tilt


SWEEP_PERIOD = 300
SETTLE_SECONDS = 1.0


def sample(tilt):
    result = self.set_tilt(tilt)
    if result.status != "ok":
        raise RuntimeError("set_tilt " + result.status)
    sleep(SETTLE_SECONDS)
    return self.get_output()


while True:
    try:
        best = choose_tilt(sample)
        self.set_tilt(best)
        set_status("tilt " + str(round(best, 1)) + " deg", "info")
    except RuntimeError as error:
        set_status(str(error), "error")
    sleep(SWEEP_PERIOD)
