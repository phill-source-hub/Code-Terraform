"""Charging station: charge every vehicle parked here to full, and send a drone to stranded rovers.

Where it runs: machine script slot `charging_station_1` (self = the station, Mk II or Mk III).
Why: a rover cannot charge itself. charge() is self-only on the station, so this script queues
    each docked vehicle. A vehicle already charging, queued or full is left alone, so the queue
    is not refilled every poll.
Rescue: a rover that runs dry in the field has status "stranded" and is not docked here, so the
    station cannot see it through get_docked(). This script checks the vehicles in RESCUE_VEHICLES
    by id and sends the service drone to the first stranded one. The drone charges it where it
    stands (manual, Batteries and Charging). Only one drone flies at a time, so the check waits
    until is_rescuing() is False. Dispatch needs station power; a refusal is reported once, not
    every poll.
Parking: a vehicle charges only while parked in this station's service area (manual, Charging
    Stations). The rover's own script chooses the station with dock() when there are several.
API facts relied on (docs/game/manual, Vehicle Charging Station): self.get_docked() -> list of
    ids; self.status(vehicle_id) -> dict with "state"; self.charge(vehicle_id, target_level) ->
    ActionResult (.status); self.is_rescuing() -> bool; self.dispatch_rescue(vehicle_name,
    target_level) -> ActionResult (.status, .message); get_component(id).status() for a rover
    (docs/game/rover.md); set_status; sleep.
Pacing: one poll every POLL_S seconds. This is a service loop, so it runs until the owner stops it.
"""

CHARGE_TARGET = 1.0
RESCUE_TARGET = 1.0
POLL_S = 5
# Rovers this station will fetch when they strand. Add a Pioneer id here to rescue it too.
RESCUE_VEHICLES = ("rover_1",)
ALREADY_HANDLED = ("charging", "queued", "target_reached")
ACCEPTED = ("charging", "queued", "target_reached")
DISPATCHED = ("ok",)


def handle_docked():
    for vehicle_id in self.get_docked():
        state = self.status(vehicle_id)
        if state.get("state") in ALREADY_HANDLED:
            continue
        result = self.charge(vehicle_id, CHARGE_TARGET)
        if result.status not in ACCEPTED:
            set_status("charge " + vehicle_id + " " + result.status + ": " + result.message, "warn")


def handle_rescue(notes):
    """Send the drone to the first stranded rover in RESCUE_VEHICLES, if no drone is out.

    `notes` remembers the last refusal per rover, so a refusal that repeats every poll is shown
    once. A successful dispatch clears it.
    """
    if self.is_rescuing():
        return
    for vehicle_id in RESCUE_VEHICLES:
        vehicle = get_component(vehicle_id)
        if vehicle is None or vehicle.status() != "stranded":
            continue
        result = self.dispatch_rescue(vehicle_id, RESCUE_TARGET)
        if result.status in DISPATCHED:
            notes[vehicle_id] = None
            set_status("rescue drone sent to " + vehicle_id, "info")
        elif notes.get(vehicle_id) != result.status:
            notes[vehicle_id] = result.status
            set_status("rescue " + vehicle_id + " " + result.status + ": " + result.message, "warn")
        return


notes = {}
while True:
    handle_docked()
    handle_rescue(notes)
    sleep(POLL_S)
