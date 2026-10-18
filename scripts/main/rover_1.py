"""Rover: survey the whole map once, then mine the best reachable site and bring the ore home.

Where it runs: machine script slot `rover_1` (self = this rover). Needs Nav, Sonar, Drill mounted.
Imports the `rover_plan` Library for stops, tier choice, target choice and energy gates.
Phases:
    1. Survey (once, unless the Data Archive already holds a map): drive a grid of stops sized to
       the mounted sonar range, scan and survey at each, then visit each contact the grid did not
       resolve, once. The map (base at 0, 0, contacts, sites) goes to the Data Archive as MAP_KEY
       and is printed.
    2. Mine, repeated: at base, unload the hold to Inventory and swap in the best drill from
       Base Inventory. Then pick the best surveyed site the mounted drill can cut, drive there,
       mine until the hold is full or the return reserve is reached, and drive home.
    3. Recharge: any leg that would leave less charge than the way home needs first goes home
       and waits there. The Charging Station's script (charging_station_1) charges the parked rover.
Bounds: every drive stops on arrival, on a stall, on the tick limit or on low charge. Every wait
    has a tick limit. Nothing here calls a game action that the status literal does not confirm.
Why the reserve is checked at each visit: a rover that strands away from base is rescued slowly
    (manual, Batteries and Charging), so it turns back before the charge runs out.
API facts relied on (docs/game/rover.md, manual): self.nav.set_target, set_throttle, brake,
    get_distance_to, get_position; self.sonar.scan, survey, range; self.drill.mine;
    self.battery.level, wh; self.cargo.count, stacks; self.output.connect, send; self.modules(),
    self.mount, self.unmount (MountSlot .index .type .module_id); get_component("nocturna")
    .get_bounds, points_of_interest; get_component("journal").discovered_sites;
    get_component("notebook").has, set; get_component("inventory").count; sleep, set_status.
"""

from rover_plan import (
    DEFAULT_WH_PER_M,
    DRILL_TIERS,
    STOP_SPACING_FACTOR,
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
    survey_stops,
)

MAP_KEY = "rover.map"
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


def drive_to(x, y):
    """Drive to (x, y) and brake. True only if the rover is within arrival range at the end."""
    self.nav.set_target(x, y)
    self.nav.set_throttle(CRUISE)
    best = self.nav.get_distance_to(x, y)
    stalled = 0
    for _ in range(MAX_DRIVE_TICKS):
        remaining = self.nav.get_distance_to(x, y)
        if arrived(remaining):
            break
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
    """Drive to (x, y) if the trip and the way home fit the charge, otherwise recharge first."""
    if not affordable(position(), (x, y), state["wh_per_m"]) and not recharge_at_home():
        return False
    before = self.battery.wh()
    start = position()
    reached = drive_to(x, y)
    metres = distance(start, position())
    state["wh_per_m"] = calibrated_wh_per_m(state["wh_per_m"], before - self.battery.wh(), metres)
    return reached


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


def survey_map(state):
    bounds_box = get_component("nocturna").get_bounds()
    bounds = (bounds_box.min_x, bounds_box.max_x, bounds_box.min_y, bounds_box.max_y)
    spacing = self.sonar.range() * STOP_SPACING_FACTOR
    stops = survey_stops(bounds, spacing)
    for index, (x, y) in enumerate(stops):
        set_status("survey stop " + str(index + 1) + " of " + str(len(stops)), "info")
        if visit(x, y, state):
            scan_here()
        else:
            print("skipped stop " + str(x) + ", " + str(y))
    # One pass over the contacts the grid left unresolved. A contact still unscanned after its
    # visit is blocked; it is not revisited, so the pass always ends.
    for point in pending_contacts([_point(p) for p in contacts()], set()):
        if visit(point["x"], point["y"], state):
            scan_here()
    return bounds


def _point(p):
    return {"x": p.x, "y": p.y, "scanned": p.scanned, "kind": p.kind}


def site_record(site):
    kind = site.kind()
    record = {"id": site.id, "x": site.x, "y": site.y, "kind": kind}
    record.update({"item_id": None, "hardness": None, "purity": None})
    if kind == "mineral":
        record.update({"item_id": site.item_id, "hardness": site.hardness, "purity": site.purity})
    return record


def save_map(bounds):
    journal = get_component("journal")
    sites = [site_record(s) for s in journal.discovered_sites("nocturna")]
    contact_list = [_point(p) for p in contacts()]
    grid_map = build_map(bounds, contact_list, sites, HOME)
    notebook = get_component("notebook")
    if notebook is not None:
        saved = notebook.set(MAP_KEY, grid_map)
        if saved.status != "ok":
            set_status("map save " + saved.status + ": " + saved.message, "warn")
    print("map: " + str(len(contact_list)) + " contacts, " + str(len(sites)) + " sites")
    return grid_map


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
    if arrived(distance(position(), HOME)):
        unload_cargo()
        refresh_drill()
    drill_id = mounted_drill_id()
    if drill_id is None:
        set_status("no drill mounted; resting", "warn")
        return rest()
    here = position()
    pick = choose_target(
        mineral_sites(),
        drill_id=drill_id,
        position=here,
        home=HOME,
        charge_wh=self.battery.wh(),
        wh_per_m=state["wh_per_m"],
        cargo_free=VEHICLE_CARGO_CAPACITY - self.cargo.count(),
    )
    if pick is None:
        set_status("no surveyed site reachable on this charge; resting at base", "info")
        if visit(HOME[0], HOME[1], state):
            unload_cargo()
        return rest()
    site = pick["site"]
    set_status("mining " + site["id"] + " (" + site["item_id"] + ")", "info")
    if not visit(site["x"], site["y"], state):
        set_status("could not reach " + site["id"] + "; will retry", "warn")
        return
    mined = mine_units(pick["units"], state)
    print("mined " + str(mined) + " from " + site["id"])
    if visit(HOME[0], HOME[1], state):
        unload_cargo()


def rest():
    for _ in range(REST_TICKS):
        sleep(TICK_S)


def main():
    state = {"wh_per_m": DEFAULT_WH_PER_M}
    notebook = get_component("notebook")
    if notebook is None or not notebook.has(MAP_KEY):
        bounds = survey_map(state)
        save_map(bounds)
    while True:
        mine_cycle(state)
        # A cycle that fails at once (unreachable site, no charge) must still let time pass.
        sleep(TICK_S)


main()
