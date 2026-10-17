"""Base-wide rules for the base_watch Automation: heartbeat staleness and the status line.

Where it runs: Library (game `lib/base_watch.py`), imported by scripts/automations/base_watch.py.
No game calls here. Inputs are plain numbers and names; the Automation reads the bus.
Heartbeat (ADR-028): a machine broadcasts `status.<slot>` each pass. Its age is the simulation
    seconds since that broadcast (Signal Bus, `latest_info().age_seconds`, docs/game/signal-bus.md).
    A machine with no broadcast has no age and is reported as not yet reporting.
"""


def heartbeat_alerts(ages, stale_seconds):
    """Alerts for machines whose last heartbeat is missing or older than stale_seconds.

    `ages` maps a machine slot to the age in seconds of its last heartbeat, or to None when it
    has never reported (or the bus gives no age). Machines are listed in name order so the
    output does not change from one pass to the next.
    """
    alerts = []
    for name in sorted(ages):
        age = ages[name]
        if age is None:
            alerts.append(f"{name}: no heartbeat yet")
        elif age > stale_seconds:
            alerts.append(f"{name}: silent for {age:.0f} s")
    return alerts


def status_text(alerts):
    """One line for the status bar: "base ok", or the count and the first alert."""
    if not alerts:
        return "base ok"
    return f"{len(alerts)} alert(s): {alerts[0]}"
