"""Pure tilt logic for the solar tracker. No game calls here.

Where it runs: Library. Tested source for the solar machine script (ADR-014 copy).
Rule (docs/game/power.md, Clock and Solar Generator): the panel produces most when its tilt
    complements the sun's elevation, so tilt = 90 - elevation. At night the elevation is 0,
    which gives tilt 90, the panel's rest angle.
Inputs: sun elevation in degrees, 0-90, from clock.get_elevation().
"""

TILT_MIN = 0.0
TILT_MAX = 90.0


def clamp_tilt(tilt: float) -> float:
    """Keep a tilt inside the panel's 0-90 degree range."""
    return min(max(tilt, TILT_MIN), TILT_MAX)


def target_tilt(elevation: float) -> float:
    """Panel tilt that faces the sun, given its elevation above the horizon."""
    return clamp_tilt(TILT_MAX - elevation)
