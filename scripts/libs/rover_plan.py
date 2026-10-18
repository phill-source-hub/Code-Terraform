"""Rover planning: survey stops, module tier choice, target choice and energy gates. No game calls.

Where it runs: Library (game `lib/rover_plan.py`). Imported by rover_1.
Coordinates: metres from base, base at (0, 0) (manual, Rover and Nav Module).
Inputs: plain numbers, tuples and dicts. The adapter converts game objects before calling in.
Assumptions:
    - Energy per metre is a measured or conservative number passed in. The manual does not give
      it, so the adapter starts from DEFAULT_WH_PER_M and calibrates after a leg.
    - Mining minutes per unit come from the manual's table (Battery and Charging). An unknown
      item id uses the slowest listed mineral, so the energy estimate errs high.
API facts relied on: none directly. Item ids are the Shop ids in docs/game/manual (Item Catalog).
"""

import math

ARRIVE_M = 2.0
RETURN_MARGIN = 1.2
RETURN_BUFFER_WH = 5.0
DEFAULT_WH_PER_M = 0.05

# Drill Module tiers by hardness limit (manual, Drill Module and Item Catalog).
DRILL_TIERS = {
    "drill_module": {"hardness": 1, "watts": 10, "speed": 1.0},
    "drill_module_industrial": {"hardness": 3, "watts": 20, "speed": 0.75},
    "drill_module_heavy": {"hardness": 4, "watts": 30, "speed": 0.6},
}
SONAR_TIERS = {
    "sonar_module": {"range_m": 50},
    "sonar_module_wide": {"range_m": 180},
    "sonar_module_deep": {"range_m": 280},
}
PURITY_MULTIPLIER = {"standard": 1, "rich": 2, "pure": 3}
# Base minutes per unit at standard purity (manual, Battery and Charging).
MINING_MINUTES = {"iron_ore": 15, "silicon": 15, "lead": 18, "titanium": 20, "cobalt": 20}
SLOWEST_MINUTES = 30
VEHICLE_CARGO_CAPACITY = 10


def distance(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def arrived(remaining_m):
    # The manual's own rule: 2 m is close enough, and arriving does not stop the rover.
    return remaining_m <= ARRIVE_M


def best_drill(owned):
    """The highest-hardness drill id in `owned`, or None if none is owned."""
    usable = [drill for drill in owned if drill in DRILL_TIERS]
    if not usable:
        return None
    return max(usable, key=lambda drill: DRILL_TIERS[drill]["hardness"])


def best_sonar(owned):
    """The longest-range sonar id in `owned`, or None if none is owned."""
    usable = [sonar for sonar in owned if sonar in SONAR_TIERS]
    if not usable:
        return None
    return max(usable, key=lambda sonar: SONAR_TIERS[sonar]["range_m"])


def route_wh(metres, wh_per_m):
    return metres * wh_per_m


def return_reserve_wh(distance_home_m, wh_per_m):
    """Charge to keep in hand, measured from the current point, to still reach base."""
    return route_wh(distance_home_m, wh_per_m) * RETURN_MARGIN + RETURN_BUFFER_WH


def unit_mining_wh(drill_id, item_id, purity):
    """Energy for one mined unit: drill watts times mining time, adjusted for speed and purity.

    Watts times hours, so a 10 W drill on a 15-minute iron unit uses 2.5 Wh (manual example).
    """
    tier = DRILL_TIERS[drill_id]
    minutes = MINING_MINUTES.get(item_id, SLOWEST_MINUTES)
    hours = minutes * tier["speed"] / PURITY_MULTIPLIER[purity] / 60
    return tier["watts"] * hours


def choose_target(sites, *, drill_id, position, home, charge_wh, wh_per_m, cargo_free):
    """The best surveyed site the drill can cut and the rover can reach and return from.

    `sites` are dicts with id, x, y, item_id, hardness, purity. Ranking: most ore per trip
    (units times purity), then the shorter trip. Returns {"site", "units", "wh"} or None.
    """
    limit = DRILL_TIERS[drill_id]["hardness"]
    best = None
    for site in sites:
        if site["hardness"] is None or site["hardness"] > limit:
            continue
        if site["item_id"] is None or site["purity"] is None:
            continue
        there = route_wh(distance((position[0], position[1]), (site["x"], site["y"])), wh_per_m)
        home_m = distance((site["x"], site["y"]), home)
        back = return_reserve_wh(home_m, wh_per_m)
        per_unit = unit_mining_wh(drill_id, site["item_id"], site["purity"])
        spare = charge_wh - there - back
        units = min(cargo_free, math.floor(spare / per_unit)) if spare > 0 else 0
        if units < 1:
            continue
        trip = route_wh(home_m, wh_per_m) + there
        value = (units * PURITY_MULTIPLIER[site["purity"]], -trip)
        if best is None or value > best[0]:
            best = (value, {"site": site, "units": units, "wh": there + units * per_unit})
    return None if best is None else best[1]


def pending_contacts(points, visited, origin=(0.0, 0.0)):
    """Unscanned contacts not yet visited, nearest to `origin` first.

    `points` are dicts with x, y, scanned. `visited` is a set of (x, y). A contact visited but
    still unscanned was blocked (the sweep could not classify it), so it is not picked again.
    Nearest-first keeps the first surveyed sites close to base, so mining can start early.
    """
    left = [p for p in points if not p["scanned"] and (p["x"], p["y"]) not in visited]
    return sorted(left, key=lambda p: distance(origin, (p["x"], p["y"])))


def calibrated_wh_per_m(current, measured_wh, metres):
    """Energy per metre from one leg, or the current value when the leg is too short to trust."""
    if metres < 10:
        return current
    return max(measured_wh / metres, 0.0)


def build_map(bounds, contacts, sites, home=(0.0, 0.0)):
    """The saved map: base, the box, every contact and every classified site, all JSON-safe."""
    min_x, max_x, min_y, max_y = bounds
    return {
        "base": {"x": home[0], "y": home[1]},
        "bounds": {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y},
        "contacts": [
            {"x": c["x"], "y": c["y"], "scanned": bool(c["scanned"]), "kind": c["kind"]}
            for c in contacts
        ],
        "sites": list(sites),
    }
