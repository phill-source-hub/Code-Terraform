"""Pure power-status logic shared by machine scripts. No game calls here.

Where it runs: Library, imported by machine scripts (game `lib/power_status.py`).
Inputs: grid snapshots from `power_control.grids()` (VERIFIED docs: PowerGrid has
    `net` W, `stored` Wh, `capacity` Wh).
Assumptions: a grid with no battery has capacity 0 and is judged on net flow only.
API facts relied on: none directly; callers pass plain numbers or grid objects.
"""

# Below this share of battery capacity, warn before the grid browns out. A judgement call,
# not a game rule: tune it after watching real nights.
LOW_STORAGE_FRACTION = 0.2


def stored_fraction(stored_wh: float, capacity_wh: float) -> float:
    """Share of battery capacity in use, clamped to 0-1. No batteries counts as 0."""
    if capacity_wh <= 0:
        return 0.0
    return min(max(stored_wh / capacity_wh, 0.0), 1.0)


def summarize_grids(grids) -> dict[str, float]:
    """Totals across every grid snapshot. Net is generation minus consumption, in W."""
    totals = {"grids": 0.0, "net": 0.0, "stored": 0.0, "capacity": 0.0}
    for grid in grids:
        totals["grids"] += 1
        totals["net"] += grid.net
        totals["stored"] += grid.stored
        totals["capacity"] += grid.capacity
    return totals


def classify(net_w: float, stored_wh: float, capacity_wh: float) -> list[str]:
    """Warning messages for the current state. An empty list means all is well."""
    alerts: list[str] = []
    if net_w < 0:
        alerts.append(f"power deficit: net {net_w:.0f} W")
    if capacity_wh > 0 and stored_fraction(stored_wh, capacity_wh) < LOW_STORAGE_FRACTION:
        alerts.append(f"low battery: {stored_fraction(stored_wh, capacity_wh):.0%} stored")
    return alerts
