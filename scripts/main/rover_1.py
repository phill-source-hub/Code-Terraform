"""Rover: survey contacts nearest base first, and mine as soon as a surveyed site is in reach.

Where it runs: machine script slot `rover_1` (self = this rover). Needs Nav, Sonar, Drill mounted.
Imports the `rover_plan` Library for contact order, tier choice, target choice and energy gates.
Loop, one pass per tick:
    1. Mine, if a surveyed mineral site is reachable on the current charge. At base first, unload
       the hold to Inventory and swap in the best drill from Base Inventory. Then drive to the best
       site, mine until the hold is full or the return reserve is reached, and drive home.
    2. Survey, once per pass after a mining trip, or whenever nothing is mineable. Visit the
       unscanned contact nearest base, scan there, survey productive hits, and save the map.
       Every contact is visited at most once. A contact still unscanned after its visit is blocked.
    3. Rest, when nothing is mineable and no contact is left.
The map (base at 0, 0, bounds, contacts, sites) is saved to the Data Archive as MAP_KEY after every
    survey visit, so it grows as the rover works. Nothing is printed except the save summary.
Recharge: any leg that would leave less charge than the way home needs first goes home and waits.
    The Charging Station's script (charging_station_1) charges the parked rover.
Bounds: every drive stops on arrival, on a stall, on the tick limit or on low charge. Every wait
    has a tick limit. Nothing here calls a game action that the status literal does not confirm.
Why nearest first: contacts are already on the map (manual, Nocturna), so no grid is needed to
    find them. Visiting near ones first makes the first mining trip short and cheap.
API facts relied on (docs/game/rover.md, manual): self.nav.set_target, set_throttle, brake,
    get_distance_to, get_position; self.sonar.scan, survey, range; self.drill.mine;
    self.battery.level, wh; self.is_being_rescued; self.cargo.count, stacks;
    self.output.connect, send; self.modules(),
    self.mount, self.unmount (MountSlot .index .type .module_id); get_component("nocturna")
    .get_bounds, points_of_interest; get_component("journal").discovered_sites, surveyed_sites;
    get_component("notebook").set; get_component("inventory").count; sleep, set_status.
"""

from rover_plan import (
    DEFAULT_WH_PER_M,
    DRILL_TIERS,
    VEHICLE_CARGO_CAPACITY,
    arrived,
    best_drill,
    build_map,
    calibrated_wh_per_m,
    choose_target,
    distance,
    pending_contacts,
    return_reserve_wh,
    route_wh,
)

MAP_KEY = "rover.map"
RATE_KEY = "rover.wh_per_m"
HOME = (0.0, 0.0)
CRUISE = 0.5
TICK_S = 1
STALL_TICKS = 30
MAX_DRIVE_TICKS = 3600
# Low enough to stop a drive before the battery is empty, high enough to leave room to come home.
LOW_LEVEL = 0.1
RECHARGE_LEVEL = 0.9
MAX_RECHARGE_TICKS = 7200
# One scan and one survey, with headroom: a visit must leave this much spare beyond the trip.
SCAN_RESERVE_WH = 1.0
REST_TICKS = 600
SURVEYED_STATUSES = ("ok", "too_hard", "tier_too_low", "research_required", "wrong_scanner")


def position():
    p = self.nav.get_position()
    return (p.x, p.y)


def drive_to(x, y, wh_per_m):
    """Drive to (x, y) and brake. True only if the rover is within arrival range at the end.

    Mid-leg check: if the charge left no longer covers the way home from here, the target is
    changed to base at once. The pre-leg check uses an estimate, so a real rate that is worse
    must not strand the rover out on the field.
    """
    target = (x, y)
    self.nav.set_target(target[0], target[1])
    self.nav.set_throttle(CRUISE)
    best = self.nav.get_distance_to(target[0], target[1])
    stalled = 0
    for _ in range(MAX_DRIVE_TICKS):
        remaining = self.nav.get_distance_to(target[0], target[1])
        if arrived(remaining):
            break
        if self.is_being_rescued():
            # A rescue drone is charging us where we stand (manual): hold, and do not count the wait
            # as a stall or the low-charge check as a reason to give up the leg.
            sleep(TICK_S)
            continue
        if target != HOME and self.battery.wh() < return_reserve_wh(
            distance(position(), HOME), wh_per_m
        ):
            target = HOME
            self.nav.set_target(HOME[0], HOME[1])
            best = self.nav.get_distance_to(HOME[0], HOME[1])
            stalled = 0
            set_status("low charge; heading home", "warn")
        if remaining < best:
            best = remaining
            stalled = 0
        else:
            stalled += 1
        if stalled >= STALL_TICKS or self.battery.level() <= LOW_LEVEL:
            break
        sleep(TICK_S)
    # Brake before any stationary action; the manual says arrival alone does not stop the rover.
    self.nav.brake()
    return arrived(self.nav.get_distance_to(x, y))


def affordable(here, target, wh_per_m):
    """Enough charge to reach `target` and still get home from it, with a scan's headroom."""
    need = route_wh(distance(here, target), wh_per_m)
    need += return_reserve_wh(distance(target, HOME), wh_per_m) + SCAN_RESERVE_WH
    return self.battery.wh() >= need


def recharge_at_home():
    """Go home and wait for the station to charge the rover. True once charge reaches the target."""
    if not arrived(distance(position(), HOME)) and not drive_to(HOME[0], HOME[1]):
        return False
    for _ in range(MAX_RECHARGE_TICKS):
        if self.battery.level() >= RECHARGE_LEVEL:
            return True
        set_status("charging at base: " + str(round(self.battery.level() * 100)) + "%", "info")
        sleep(TICK_S)
    set_status("no charge at base; check the Charging Station", "warn")
    return False


def visit(x, y, state):
    """Drive to (x, y) if the trip and the way home fit the charge, otherwise recharge first.

    Returns "arrived", "stalled" (drive ended short), "no_charge" (base could not recharge the
    rover, so the visit did not start) or "out_of_range" (the trip does not fit even on a full
    charge). Only "no_charge" is worth retrying later.
    """
    wh_per_m = state["wh_per_m"]
    if not affordable(position(), (x, y), wh_per_m):
        if not recharge_at_home():
            return "no_charge"
        if not affordable(position(), (x, y), wh_per_m):
            return "out_of_range"
    before = self.battery.wh()
    start = position()
    reached = drive_to(x, y, wh_per_m)
    metres = distance(start, position())
    state["wh_per_m"] = calibrated_wh_per_m(wh_per_m, before - self.battery.wh(), metres)
    save_rate(state)
    return "arrived" if reached else "stalled"


def save_rate(state):
    notebook = get_component("notebook")
    if notebook is not None:
        notebook.set(RATE_KEY, state["wh_per_m"])


def scan_here():
    """Sweep from the stop, survey each productive contact found, and report anything unusual."""
    sweep = self.sonar.scan()
    if sweep.status not in SURVEYED_STATUSES:
        set_status("scan " + sweep.status + ": " + sweep.message, "warn")
        return
    for found in sweep.sites:
        if found.kind() == "inert":
            continue
        result = self.sonar.survey(found)
        if result.status != "ok":
            print("survey " + found.id + ": " + result.status + " " + result.message)


def contacts():
    return get_component("nocturna").points_of_interest()


def _point(p):
    return {"x": p.x, "y": p.y, "scanned": p.scanned, "kind": p.kind}


def map_bounds():
    box = get_component("nocturna").get_bounds()
    return (box.min_x, box.max_x, box.min_y, box.max_y)


def site_record(site):
    kind = site.kind()
    record = {"id": site.id, "x": site.x, "y": site.y, "kind": kind}
    record.update({"item_id": None, "hardness": None, "purity": None})
    if kind == "mineral":
        record.update({"item_id": site.item_id, "hardness": site.hardness, "purity": site.purity})
    return record


def save_map():
    journal = get_component("journal")
    sites = [site_record(s) for s in journal.discovered_sites("nocturna")]
    contact_list = [_point(p) for p in contacts()]
    grid_map = build_map(map_bounds(), contact_list, sites, HOME)
    notebook = get_component("notebook")
    if notebook is not None:
        saved = notebook.set(MAP_KEY, grid_map)
        if saved.status != "ok":
            set_status("map save " + saved.status + ": " + saved.message, "warn")


def survey_next(state):
    """Visit the unscanned contact nearest base. True if a contact was visited."""
    pending = pending_contacts([_point(p) for p in contacts()], state["visited"], HOME)
    if not pending:
        return False
    point = pending[0]
    key = (point["x"], point["y"])
    set_status("survey " + str(len(pending)) + " contacts left", "info")
    result = visit(point["x"], point["y"], state)
    if result == "no_charge":
        # Not marked: the same contact is tried again once the rover has charge.
        return True
    # Marked visited for any other result, so an unreachable or stalled contact cannot hold the
    # loop. A restart clears the list and tries again.
    state["visited"][key] = True
    if result == "arrived":
        scan_here()
    save_map()
    return True


def mounted_drill_slot():
    for slot in self.modules():
        if slot.module_id in DRILL_TIERS:
            return slot
        if slot.module_id is None and slot.type in ("drill_basic", "universal"):
            return slot
    return None


def owned_drills(slot):
    owned = [drill for drill in DRILL_TIERS if get_component("inventory").count(drill) > 0]
    if slot is not None and slot.module_id in DRILL_TIERS:
        owned.append(slot.module_id)
    return owned


def refresh_drill():
    """At base: swap in the highest drill tier in Base Inventory; otherwise keep the current one."""
    slot = mounted_drill_slot()
    if slot is None:
        set_status("no drill slot on this rover", "error")
        return
    best = best_drill(owned_drills(slot))
    if best is None or best == slot.module_id:
        return
    if slot.module_id is not None:
        taken_off = self.unmount(slot.index)
        if taken_off.status != "ok":
            set_status("unmount " + taken_off.status + ": " + taken_off.message, "warn")
            return
    fitted = self.mount(slot.index, best)
    if fitted.status != "ok":
        # The old drill is back in Inventory, so the rover stays usable. Keep going with it.
        set_status("mount " + best + " " + fitted.status + ": " + fitted.message, "warn")


def mounted_drill_id():
    slot = mounted_drill_slot()
    if slot is None or slot.module_id not in DRILL_TIERS:
        return None
    return slot.module_id


def unload_cargo():
    if self.cargo.count() == 0:
        return
    connected = self.output.connect("inventory")
    if connected.status != "ok":
        set_status("unload " + connected.status + ": " + connected.message, "warn")
        return
    for stack in self.cargo.stacks():
        moved = self.output.send(stack.id, stack.count)
        if moved.status not in ("ok", "partial"):
            set_status("unload " + moved.status + ": " + moved.message, "warn")


def mine_units(units, state):
    mined = 0
    while mined < units and self.cargo.count() < VEHICLE_CARGO_CAPACITY:
        spare = self.battery.wh() - return_reserve_wh(distance(position(), HOME), state["wh_per_m"])
        if spare <= 0:
            break
        result = self.drill.mine()
        if result.status != "ok":
            set_status("mine " + result.status + ": " + result.message, "warn")
            break
        mined += 1
    return mined


def mineral_sites():
    journal = get_component("journal")
    return [site_record(s) for s in journal.surveyed_sites("nocturna") if s.kind() == "mineral"]


def mine_cycle(state):
    """One mining trip if a surveyed site is reachable. True if a trip was attempted."""
    if arrived(distance(position(), HOME)):
        unload_cargo()
        refresh_drill()
    drill_id = mounted_drill_id()
    if drill_id is None:
        set_status("no drill mounted; resting", "warn")
        return False
    pick = choose_target(
        mineral_sites(),
        drill_id=drill_id,
        position=position(),
        home=HOME,
        charge_wh=self.battery.wh(),
        wh_per_m=state["wh_per_m"],
        cargo_free=VEHICLE_CARGO_CAPACITY - self.cargo.count(),
    )
    if pick is None:
        return False
    site = pick["site"]
    set_status("mining " + site["id"] + " (" + site["item_id"] + ")", "info")
    if visit(site["x"], site["y"], state) != "arrived":
        set_status("could not reach " + site["id"] + "; will retry", "warn")
        return True
    mined = mine_units(pick["units"], state)
    print("mined " + str(mined) + " from " + site["id"])
    if visit(HOME[0], HOME[1], state) == "arrived":
        unload_cargo()
    return True


def rest():
    for _ in range(REST_TICKS):
        sleep(TICK_S)


def start_rate():
    # The measured rate survives a restart, so the first legs after one use a real number.
    notebook = get_component("notebook")
    if notebook is not None and notebook.has(RATE_KEY):
        stored = notebook.get(RATE_KEY, DEFAULT_WH_PER_M)
        if isinstance(stored, float) and stored > 0:
            return stored
    return DEFAULT_WH_PER_M


def main():
    state = {"wh_per_m": start_rate(), "visited": {}}
    while True:
        if mine_cycle(state):
            # Survey one contact after each trip, so the map keeps growing while mining.
            survey_next(state)
        elif not survey_next(state):
            set_status("all contacts surveyed; resting at base", "info")
            if visit(HOME[0], HOME[1], state) == "arrived":
                unload_cargo()
            rest()
        # A pass that does nothing (no site, no contact) must still let time pass.
        sleep(TICK_S)


main()
