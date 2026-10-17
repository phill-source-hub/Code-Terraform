"""Power monitor: warn on a grid deficit or low battery. Read-only.

Where it runs: machine script slot `harvester_1` (game file `harvester_1.py`). Placed here
as the first real script; it does not use the harvester.
Inputs: none. Reads `power_control.grids()` every POLL_SECONDS of game time.
Assumptions: `power_control` is a component id in the save (VERIFIED docs example). Logic
lives in the `power_status` Library so tests run outside the game.
API facts relied on (see docs/game/power.md): get_component, PowerGrid.net/stored/capacity,
warn, print, set_status, sleep. Prints and warnings fire only when the message changes.
"""

from power_status import classify, summarize_grids

POLL_SECONDS = 5

power = get_component("power_control")
if power is None:
    set_status("power_control not found", "error")
else:
    last_message = None
    while True:
        totals = summarize_grids(power.grids())
        alerts = classify(totals["net"], totals["stored"], totals["capacity"])
        message = "; ".join(alerts) or "power ok"
        if message != last_message:
            if alerts:
                warn(message)
            else:
                print(message)
            last_message = message
        set_status(message, "warn" if alerts else "info")
        sleep(POLL_SECONDS)
