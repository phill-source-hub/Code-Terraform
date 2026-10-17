"""Power monitor: warn on a grid deficit or low battery. Read-only.

Where it runs: machine script slot `harvester_1` (game file `harvester_1.py`). Placed on this
    free slot as the first real script; it does not use the harvester.
Self-contained on purpose (ADR-014): no imports. The rules are a copy of
    scripts/libs/power_status.py. Tests check the copy gives the same messages.
Inputs: none. Reads power_control.grids() every POLL_SECONDS of game time.
Output: a message prints (or warns) only when it changes; status shows the current state.
API facts relied on (docs/game/power.md): get_component, power_control.grids(), PowerGrid
    .net (W), .stored (Wh), .capacity (Wh); warn, print, set_status, sleep.
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
if power is None:
    set_status("power_control not found", "error")
else:
    last_message = None
    while True:
        net, stored, capacity = totals(power.grids())
        alerts = classify(net, stored, capacity)
        message = "; ".join(alerts) or "power ok"
        if message != last_message:
            if alerts:
                warn(message)
            else:
                print(message)
            last_message = message
        set_status(message, "warn" if alerts else "info")
        sleep(POLL_SECONDS)
