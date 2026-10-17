"""Power monitor: warn on a grid deficit or low battery. Read-only. PARKED (not synced).

Parked in scripts/parked/ because harvester_1 now runs the harvester. Needs a free machine slot
    before it can run in game again (owner to choose). Copy to scripts/main/ with a new name,
    then sync.
Self-contained on purpose (ADR-014): no imports. The rules are a copy of
    scripts/libs/power_status.py. Tests check the copy gives the same messages.
Inputs: none. Reads power_control.grids() and battery_1 every POLL_SECONDS of game time.
Output: a grid message prints (or warns) only when it changes. The status line always shows
    the grid state and battery_1's charge; battery_1 low (under 20%) is a warning.
API facts relied on (docs/game/power.md): get_component, power_control.grids(), PowerGrid
    .net (W), .stored (Wh), .capacity (Wh), Battery .get_level() and .get_capacity() (Wh);
    warn, print, set_status, sleep.
"""

POLL_SECONDS = 5
LOW_STORAGE_FRACTION = 0.2


def stored_fraction(stored_wh, capacity_wh):
    if capacity_wh <= 0:
        return 0.0
    return min(max(stored_wh / capacity_wh, 0.0), 1.0)


def classify(net_w, stored_wh, capacity_wh):
    alerts = []
    if net_w < 0:
        alerts.append("power deficit: net " + str(round(net_w)) + " W")
    if capacity_wh > 0 and stored_fraction(stored_wh, capacity_wh) < LOW_STORAGE_FRACTION:
        alerts.append(
            "low battery: " + str(round(stored_fraction(stored_wh, capacity_wh) * 100)) + "% stored"
        )
    return alerts


def battery_percent(battery):
    if battery is None:
        return None
    capacity = battery.get_capacity()
    if capacity <= 0:
        return None
    return round(battery.get_level() / capacity * 100)


def totals(grids):
    net = 0.0
    stored = 0.0
    capacity = 0.0
    for grid in grids:
        net += grid.net
        stored += grid.stored
        capacity += grid.capacity
    return net, stored, capacity


power = get_component("power_control")
battery = get_component("battery_1")
if power is None:
    set_status("power_control not found", "error")
else:
    last_message = None
    while True:
        net, stored, capacity = totals(power.grids())
        alerts = classify(net, stored, capacity)
        percent = battery_percent(battery)
        if percent is not None and percent < LOW_STORAGE_FRACTION * 100:
            alerts.append("battery_1 low: " + str(percent) + "%")
        message = "; ".join(alerts) or "power ok"
        if message != last_message:
            if alerts:
                warn(message)
            else:
                print(message)
            last_message = message
        status = message
        if percent is not None:
            status = status + " | battery_1 " + str(percent) + "%"
        set_status(status, "warn" if alerts else "info")
        sleep(POLL_SECONDS)
