"""Pure logic for the Control Room dashboards. No game calls here.

Where it runs: Library, imported by Control Room card scripts (game `lib/control_room.py`).
Inputs: plain numbers and strings that the card scripts read from game snapshots.
Assumptions: runway is stored energy over net drain, so it reads in game hours.
API facts relied on: none directly. Field names used by the cards come from the game stub
    (VERIFIED stub): PowerGrid, VehicleRef, DroneRef, Order, BroadcastInfo.
"""

# Manual: batteries plus Lightning reserve hold one hour of deficit before recovery. The
# warning band above that is a judgement call; tune it after watching a real night.
RUNWAY_WARN_HOURS = 2.0
RUNWAY_CRITICAL_HOURS = 1.0

# Statuses from the stub's VehicleRef / DroneRef. Red needs a rescue or a fix now; amber is a
# wait the player may want to see.
# Tuples, not sets: the game has no set or frozenset builtin (only the names in the stub).
RED_STATUSES = (
    "stranded",
    "scrambled",
    "stalled_no_battery",
    "stalled_no_oil",
    "stalled_no_route",
)
AMBER_STATUSES = (
    "waiting_service",
    "waiting_oil",
    "waiting_bay",
    "holding_weather",
    "being_rescued",
)

CHANNEL_MAX_LENGTH = 64


def runway_hours(net_w, stored_wh, reserve_wh=0.0):
    """Game hours of storage left at the current deficit. Infinite when net is not negative."""
    if net_w >= 0:
        return float("inf")
    return max(stored_wh + reserve_wh, 0.0) / -net_w


def runway_band(hours):
    """Band for a runway value: "ok", "warn" or "critical"."""
    if hours < RUNWAY_CRITICAL_HOURS:
        return "critical"
    if hours < RUNWAY_WARN_HOURS:
        return "warn"
    return "ok"


# Dots take status names; bars take the theme tokens from the Control Room brief.
BAND_DOT = {"ok": "running", "warn": "paused", "critical": "error"}
BAND_TOKEN = {"ok": "success", "warn": "warning", "critical": "error"}
FLEET_DOT = {"green": "running", "amber": "paused", "red": "error"}
FLEET_TOKEN = {"green": "success", "amber": "warning", "red": "error"}


def fraction_of(value, capacity):
    """Share of a capacity, clamped to 0-1. No capacity counts as 0."""
    if capacity <= 0:
        return 0.0
    return min(max(value / capacity, 0.0), 1.0)


def grid_storage_fraction(stored_wh, capacity_wh, reserve_wh, reserve_capacity_wh):
    """Share of all storage in a grid, conventional batteries and Lightning reserve together."""
    return fraction_of(stored_wh + reserve_wh, capacity_wh + reserve_capacity_wh)


def fleet_color(status):
    """ "red", "amber" or "green" for a vehicle or drone status string."""
    if status in RED_STATUSES:
        return "red"
    if status in AMBER_STATUSES:
        return "amber"
    return "green"


# Status dot states the game draws (stub: status_dot). Alert levels above use the same names.
DOT_FOR_COLOR = {"red": "error", "amber": "paused", "green": "running"}


def fleet_sort_key(row):
    """Red first, then amber, then green; names break ties so the board does not jump."""
    order = {"red": 0, "amber": 1, "green": 2}
    return (order[row["color"]], row["name"])


def order_totals(requires, shipped):
    """(delivered, needed) units for an order. Each item counts only up to what it asked for."""
    needed = sum(requires.values())
    done = 0
    for item_id, count in requires.items():
        done += min(shipped.get(item_id, 0), count)
    return done, needed


def order_progress(requires, shipped):
    """Share of an order delivered, 0-1. An order that asks for nothing counts as 0."""
    done, needed = order_totals(requires, shipped)
    if needed <= 0:
        return 0.0
    return done / needed


def unit_fraction(engine, battery_wh, battery_capacity, oil_tons, oil_capacity):
    """Fill share for a vehicle or drone bar: oil for heli drones, battery for everything else.

    Missing values (a heli drone has no battery reading, an electric one no oil) count as 0.
    """
    if engine == "heli":
        return fraction_of(oil_tons or 0.0, oil_capacity or 0.0)
    return fraction_of(battery_wh or 0.0, battery_capacity or 0.0)


def valid_channel(name):
    """True if a Signal Bus channel name is 1-64 characters of letters, digits, _ . : or -."""
    if not isinstance(name, str) or not 1 <= len(name) <= CHANNEL_MAX_LENGTH:
        return False
    for ch in name:
        is_letter = "a" <= ch <= "z" or "A" <= ch <= "Z"
        is_digit = "0" <= ch <= "9"
        if not (is_letter or is_digit or ch in "_.:-"):
            return False
    return True


def short_text(value, width):
    """`value` as text, cut to `width` characters with a marker when it does not fit."""
    text = str(value)
    if len(text) <= width:
        return text
    return text[: max(width - 3, 0)] + "..."


def format_message(message_id, sender, tick, value, width=50):
    """One Signal Bus queue entry as a single line for the monitor card."""
    return (
        "#"
        + str(message_id)
        + " "
        + str(sender)
        + " t"
        + str(tick)
        + " "
        + short_text(value, width)
    )


def alert_lines(net_w, runway, fleet_red_count, o2_missing):
    """Alert strip for the base overview: a list of (level, text), most urgent first.

    `runway` is the worst grid runway in hours (inf when no grid drains).
    """
    alerts = []
    band = runway_band(runway)
    if band == "critical":
        alerts.append(("error", "Power: under 1 h of storage at current deficit"))
    elif band == "warn":
        alerts.append(("paused", "Power: under 2 h of storage at current deficit"))
    if fleet_red_count > 0:
        alerts.append(("error", str(fleet_red_count) + " vehicle or drone needs attention"))
    if o2_missing:
        alerts.append(("paused", "Oxygen sensor not repaired: O2 reads unavailable"))
    if not alerts and net_w >= 0:
        alerts.append(("running", "All systems nominal"))
    return alerts
