"""Split a long rest into short steps so a resting machine can keep its heartbeat fresh.

Where it runs: Library (game `lib/pacing.py`), used by scanner_1 and harvester_1. No game calls.
Why (ADR-031): a machine that sleeps an hour posts no heartbeat for an hour, and the base
watch would report it silent. Sleeping in steps and posting a heartbeat each step keeps the
age under the watch's limit. HEARTBEAT_STEP_SECONDS must stay well under that limit.
"""

HEARTBEAT_STEP_SECONDS = 30


def split_sleep(seconds, step):
    """The sleep lengths that add up to `seconds`, each at most `step` long.

    A non-positive total gives no steps, so a caller that asks for no rest does not sleep.
    The last step carries the remainder, so the parts always add up exactly.
    """
    if seconds <= 0:
        return []
    parts = []
    remaining = seconds
    while remaining > step:
        parts.append(step)
        remaining = remaining - step
    parts.append(remaining)
    return parts
