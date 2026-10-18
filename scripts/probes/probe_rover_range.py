"""Probe: speed and energy per metre at three throttles, on a short out-and-back run from base.

Where it runs: Run Script in Game on `rover_1`. STOP the rover's main script first: two scripts
    cannot drive one rover. The rover must be parked at base with battery at or above 90%.
Route: base -> 30 m out -> base, at throttle 0.3, 0.5 and 1.0. About 360 m in total. The rover
    never goes far, so a stranded rover is unlikely; the abort rule below covers the rest.
Logged per leg (one line each): throttle, direction, metres driven (summed from positions read
    every tick), game hours taken (clock.elapsed_game_hours), m/h, Wh used, Wh per metre, mean
    get_speed() reading, ticks, end battery level.
Logged per throttle (summary): Wh per metre over out and back, mean m/h, and range per charge
    (100 Wh divided by Wh per metre). The range is EXTRAPOLATED from a short run, not driven.
Safety: a leg aborts (and the probe stops) if the battery falls below ABORT_LEVEL or a leg runs
    past MAX_TICKS. The rover brakes at base after every leg and at the end.
API facts relied on (docs/game/rover.md, manual): self.nav.set_target, set_throttle, brake,
    get_distance_to, get_position, get_speed; self.battery.level, wh, capacity;
    get_component("clock").elapsed_game_hours; print; sleep.
"""

import math

THROTTLES = (0.3, 0.5, 1.0)
LEG_M = 30.0
HOME = (0.0, 0.0)
ARRIVE_M = 2.0
MAX_TICKS = 7200
ABORT_LEVEL = 0.5
START_LEVEL = 0.9
TICK_S = 1

clock = get_component("clock")


def pos():
    p = self.nav.get_position()
    return (p.x, p.y)


def leg(target, throttle, label):
    """Drive one leg and print its numbers. Returns a dict, or None if the probe must stop."""
    start_wh = self.battery.wh()
    start_hours = clock.elapsed_game_hours()
    self.nav.set_target(target[0], target[1])
    self.nav.set_throttle(throttle)
    metres = 0.0
    last = pos()
    speeds = []
    ticks = 0
    while ticks < MAX_TICKS:
        if self.nav.get_distance_to(target[0], target[1]) <= ARRIVE_M:
            break
        if self.battery.level() < ABORT_LEVEL:
            print("ABORT: battery below " + str(ABORT_LEVEL) + " on the " + label + " leg")
            self.nav.brake()
            return None
        sleep(TICK_S)
        now = pos()
        metres += math.hypot(now[0] - last[0], now[1] - last[1])
        last = now
        speeds.append(self.nav.get_speed())
        ticks += 1
    self.nav.brake()
    hours = clock.elapsed_game_hours() - start_hours
    used = start_wh - self.battery.wh()
    if ticks >= MAX_TICKS:
        print("ABORT: " + label + " leg ran past " + str(MAX_TICKS) + " ticks")
        return None
    mph = metres / hours if hours > 0 else 0.0
    whpm = used / metres if metres > 0 else 0.0
    mean_speed = sum(speeds) / len(speeds) if speeds else 0.0
    print(
        "leg throttle "
        + str(throttle)
        + " "
        + label
        + ": "
        + str(round(metres, 1))
        + " m in "
        + str(round(hours, 3))
        + " h = "
        + str(round(mph, 1))
        + " m/h, "
        + str(round(used, 3))
        + " Wh, "
        + str(round(whpm, 4))
        + " Wh/m, mean get_speed "
        + str(round(mean_speed, 1))
        + ", ticks "
        + str(ticks)
        + ", end battery "
        + str(round(self.battery.level(), 3))
    )
    return {"m": metres, "h": hours, "wh": used}


def main():
    print("start: game hours " + str(round(clock.elapsed_game_hours(), 3)))
    if self.battery.level() < START_LEVEL or math.hypot(pos()[0], pos()[1]) > ARRIVE_M:
        print("abort: park at base with battery at or above " + str(START_LEVEL))
        return
    capacity = self.battery.capacity()
    for throttle in THROTTLES:
        self.nav.set_throttle(throttle)
        out = leg((LEG_M, 0.0), throttle, "out")
        if out is None:
            return
        back = leg(HOME, throttle, "back")
        if back is None:
            return
        # The arrival check can end a leg just under the floor, so check again before the next one.
        if self.battery.level() < ABORT_LEVEL:
            print("ABORT: battery below " + str(ABORT_LEVEL) + " after the back leg; stopping")
            return
        metres = out["m"] + back["m"]
        hours = out["h"] + back["h"]
        used = out["wh"] + back["wh"]
        whpm = used / metres if metres > 0 else 0.0
        mph = metres / hours if hours > 0 else 0.0
        range_m = capacity / whpm if whpm > 0 else 0.0
        range_h = range_m / mph if mph > 0 else 0.0
        print(
            "summary throttle "
            + str(throttle)
            + ": "
            + str(round(whpm, 4))
            + " Wh/m, "
            + str(round(mph, 1))
            + " m/h, EXTRAPOLATED range per charge "
            + str(round(range_m))
            + " m (about "
            + str(round(range_h, 1))
            + " h at this speed)"
        )
    self.nav.set_throttle(0.0)
    print("end: game hours " + str(round(clock.elapsed_game_hours(), 3)))


main()
