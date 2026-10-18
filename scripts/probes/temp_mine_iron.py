"""Temporary: mine the iron ore site nearest base, bring the ore home, and repeat a few times.

Where it runs: Run Script in Game on `rover_1`. STOP the rover's main script first. The rover must
    be parked at base with a drill mounted. Uses the `rover_plan` Library already in game.
Picks: surveyed mineral sites with item_id "iron_ore" that the mounted drill can cut, nearest to
    base (0, 0). No other ranking.
Trip: drive there, brake, mine until the hold is full or the return reserve is reached, drive home,
    unload to Inventory. The trip is skipped if the charge does not cover it; the rover then
    recharges at base once, and stops if the trip still does not fit.
Bounds: MAX_TRIPS trips, every drive stops on arrival or a stall, every wait has a tick limit.
API facts relied on (docs/game/rover.md, manual): self.nav.set_target, set_throttle, brake,
    get_distance_to, get_position; self.is_being_rescued; self.drill.mine; self.battery.level, wh;
    self.cargo.count, stacks; self.output.connect, send (.moved); self.modules();
    get_component("journal").surveyed_sites; sleep; print.
"""

from rover_plan import (
    DEFAULT_WH_PER_M,
    DRILL_TIERS,
    VEHICLE_CARGO_CAPACITY,
    arrived,
    distance,
    return_reserve_wh,
    route_wh,
)

ITEM = "iron_ore"
HOME = (0.0, 0.0)
WH_PER_M = DEFAULT_WH_PER_M
CRUISE = 0.5
TICK_S = 1
STALL_TICKS = 30
MAX_DRIVE_TICKS = 3600
MAX_TRIPS = 5
MINE_RESERVE_WH = 10.0
RECHARGE_LEVEL = 0.9
MAX_RECHARGE_TICKS = 7200


def position():
    p = self.nav.get_position()
    return (p.x, p.y)


def drive_to(x, y):
    """Drive to (x, y) and brake. True only if within arrival range at the end."""
    self.nav.set_target(x, y)
    self.nav.set_throttle(CRUISE)
    best = self.nav.get_distance_to(x, y)
    stalled = 0
    for _ in range(MAX_DRIVE_TICKS):
        remaining = self.nav.get_distance_to(x, y)
        if arrived(remaining):
            break
        if self.is_being_rescued():
            sleep(TICK_S)
            continue
        if remaining < best:
            best = remaining
            stalled = 0
        else:
            stalled += 1
        if stalled >= STALL_TICKS:
            break
        sleep(TICK_S)
    self.nav.brake()
    return arrived(self.nav.get_distance_to(x, y))


def mounted_drill():
    for slot in self.modules():
        if slot.module_id in DRILL_TIERS:
            return slot.module_id
    return None


def iron_sites(hardness_limit):
    found = []
    for s in get_component("journal").surveyed_sites("nocturna"):
        if s.kind() != "mineral" or s.item_id != ITEM:
            continue
        if s.hardness is None or s.hardness > hardness_limit:
            continue
        found.append(s)
    return found


def nearest(sites):
    best = None
    for s in sites:
        d = distance(HOME, (s.x, s.y))
        if best is None or d < best[0]:
            best = (d, s)
    return best


def fits(d):
    """Charge covers the trip out, the way home, and a little mining."""
    need = route_wh(d, WH_PER_M) + return_reserve_wh(d, WH_PER_M) + MINE_RESERVE_WH
    return self.battery.wh() >= need


def recharge_at_home():
    if not arrived(distance(position(), HOME)) and not drive_to(HOME[0], HOME[1]):
        return False
    for _ in range(MAX_RECHARGE_TICKS):
        if self.battery.level() >= RECHARGE_LEVEL:
            return True
        sleep(TICK_S)
    return False


def mine_load(site):
    if not drive_to(site.x, site.y):
        print("could not reach " + site.id)
        return 0
    mined = 0
    while self.cargo.count() < VEHICLE_CARGO_CAPACITY:
        spare = self.battery.wh() - return_reserve_wh(distance(position(), HOME), WH_PER_M)
        if spare <= 0:
            break
        result = self.drill.mine()
        if result.status != "ok":
            print("mine " + result.status + ": " + result.message)
            break
        mined += 1
    return mined


def deliver():
    connected = self.output.connect("inventory")
    if connected.status != "ok":
        print("connect inventory " + connected.status + ": " + connected.message)
        return 0
    delivered = 0
    for stack in self.cargo.stacks():
        moved = self.output.send(stack.id, stack.count)
        if moved.status not in ("ok", "partial"):
            print("send " + stack.id + " " + moved.status + ": " + moved.message)
        delivered += moved.moved
    return delivered


def main():
    drill_id = mounted_drill()
    if drill_id is None:
        print("no drill mounted; stopping")
        return
    limit = DRILL_TIERS[drill_id]["hardness"]
    for trip_no in range(1, MAX_TRIPS + 1):
        pick = nearest(iron_sites(limit))
        if pick is None:
            print("no surveyed iron site this drill can cut; stopping")
            return
        d, site = pick
        if not fits(d) and not (recharge_at_home() and fits(d)):
            print("cannot reach " + site.id + " on this charge; stopping")
            return
        print("trip " + str(trip_no) + ": " + site.id + " at " + str(round(d)) + " m")
        mined = mine_load(site)
        if not drive_to(HOME[0], HOME[1]):
            print("could not return home; stopping")
            return
        delivered = deliver()
        print("trip " + str(trip_no) + ": mined " + str(mined) + ", delivered " + str(delivered))
        if mined == 0:
            print("no ore mined; stopping")
            return
    print("reached " + str(MAX_TRIPS) + " trips; stopping")


main()
