"""Charging station: keep every rover or Pioneer parked at this station charging to full.

Where it runs: machine script slot `charge_station_1` (self = the station, Mk II or Mk III).
Why: a rover cannot charge itself. charge() is self-only on the station, so this script queues
    each docked vehicle. A vehicle already charging, queued or full is left alone, so the queue
    is not refilled every poll.
Parking: a vehicle charges only while parked in this station's service area (manual, Charging
    Stations). The rover's own script chooses the station with dock() when there are several.
API facts relied on (docs/game/manual, Vehicle Charging Station): self.get_docked() -> list of
    ids; self.status(vehicle_id) -> dict with "state"; self.charge(vehicle_id, target_level) ->
    ActionResult (.status); set_status; sleep.
Pacing: one poll every POLL_S seconds. This is a service loop, so it runs until the owner stops it.
"""

CHARGE_TARGET = 1.0
POLL_S = 5
ALREADY_HANDLED = ("charging", "queued", "target_reached")
ACCEPTED = ("charging", "queued", "target_reached")


def handle_docked():
    for vehicle_id in self.get_docked():
        state = self.status(vehicle_id)
        if state.get("state") in ALREADY_HANDLED:
            continue
        result = self.charge(vehicle_id, CHARGE_TARGET)
        if result.status not in ACCEPTED:
            set_status("charge " + vehicle_id + " " + result.status + ": " + result.message, "warn")


while True:
    handle_docked()
    sleep(POLL_S)
