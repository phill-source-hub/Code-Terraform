"""Pure tilt-search logic for the solar tracker. No game calls here.

Where it runs: Library, imported by the solar machine script (game `lib/solar_tracker.py`).
Inputs: `sample(tilt) -> watts`, a callable that sets the tilt and reports output.
Method: coarse scan of 0-90 degrees in COARSE_STEP steps, then a fine scan of FINE_STEP steps
    around the best coarse point. Night (no output anywhere) returns the rest angle, 90.
Assumptions: output is roughly single-peaked over tilt in one sun position. A fine-scan
    window can miss a second, higher peak elsewhere (UNVERIFIED for the game's model).
API facts relied on (docs/game/power.md): Solar Generator set_tilt clamps 0-90 and rests at 90;
    get_output returns watts. Sample count per search is about 30, bounded.
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
