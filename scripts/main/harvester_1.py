"""Harvester: collect scanned items, choosing each trip by heat cost, then store them in Inventory.

Where it runs: machine script slot `harvester_1` (self = this harvester). The harvester has no
    battery to manage; heat is its only budget (manual, Harvester: no battery is listed).
Imports the shared `grid` Library for sector names and the heat route search (ADR-025).
Position and held item: read from the game every pass (get_position, get_held). Nothing is
    assumed about the start cell.
Heat model (manual, Harvester): stepping onto an item sector +1; onto an empty sector +7;
    collecting an empty sector +9; cooling -3 per hour; cap 100. Collecting an item sector is
    assumed to add no heat (the manual states only the empty-sector cost). UNVERIFIED.
Planning, every pass: a shortest-path search from the current cell over the whole grid. Each
    step costs the heat of the cell it enters (item sector 1, anything else 7, since a collected
    or never-scanned sector is empty). Each item is then ranked by (path heat, steps). The best
    item that stays under HOT_HEAT after the trip is the target. If none is affordable, the
    harvester cools first. Replanning every pass means the route follows the latest position.
Loop, one step per pass:
    1. cool down if heat is at or above HOT_HEAT (sleep one world hour);
    2. store any held item;
    3. read the scanner snapshot; plan; pick the target;
    4. if standing on it, collect, then store; otherwise move one cardinal cell along the path.
Failure: busy or moving statuses wait SHORT_SECONDS. A refused move (invalid, too_far) drops the
    target. A full inventory waits. Every blocked path shows a status and sleeps.
API facts relied on (docs/game/harvester.md): self.get_position, self.get_held, self.get_heat,
    self.move, self.collect, self.store, get_component("scanner_1").get_scanned(),
    get_component("clock"), set_status, print, sleep.
"""

from grid import parse_sector, plan_routes, sector_id

HOT_HEAT = 80
SHORT_SECONDS = 5


scanner = get_component("scanner_1")
clock = get_component("clock")
cool_seconds = 3600
if clock is not None:
    cool_seconds = clock.real_seconds_per_hour()

done = []

while True:
    if self.get_heat() >= HOT_HEAT:
        set_status("cooling", "warn")
        sleep(cool_seconds)
        continue
    if scanner is None:
        set_status("scanner_1 not found", "error")
        sleep(cool_seconds)
        continue

    if self.get_held() != "":
        stored = self.store()
        if stored.status == "ok":
            print("stored " + str(stored.item_id) + " (was held) heat " + str(self.get_heat()))
        else:
            set_status("store " + stored.status, "warn")
            sleep(SHORT_SECONDS)
        continue

    position = parse_sector(self.get_position())
    snapshot = scanner.get_scanned()
    items = [name for name in snapshot if snapshot[name].status == "ok" and name not in done]
    if not items:
        set_status("no items to collect", "info")
        sleep(SHORT_SECONDS * 12)
        continue

    costs, first_step = plan_routes(position, items)
    heat_now = self.get_heat()
    affordable = []
    for name in items:
        heat, steps = costs[parse_sector(name)]
        if heat_now + heat < HOT_HEAT:
            affordable.append((heat, steps, name))
    if not affordable:
        set_status("cooling before the next trip", "warn")
        sleep(cool_seconds)
        continue

    target_name = min(affordable)[2]
    target = parse_sector(target_name)

    if position == target:
        pickup = self.collect()
        if pickup.status == "ok":
            done.append(target_name)
            stored = self.store()
            if stored.status == "ok":
                print(
                    "stored "
                    + str(stored.item_id)
                    + " from "
                    + target_name
                    + " heat "
                    + str(self.get_heat())
                )
            else:
                set_status("store " + stored.status, "warn")
                sleep(SHORT_SECONDS)
        elif pickup.status == "empty":
            done.append(target_name)
        elif pickup.status == "overheated":
            sleep(cool_seconds)
        else:
            set_status("collect " + pickup.status, "info")
            sleep(SHORT_SECONDS)
        continue

    step = first_step[target]
    moved = self.move(sector_id(step[0], step[1]))
    if moved.status == "overheated":
        sleep(cool_seconds)
    elif moved.status in ("moving", "busy"):
        sleep(SHORT_SECONDS)
    elif moved.status not in ("ok", "already_here"):
        done.append(target_name)
        set_status("move " + moved.status + " to " + target_name, "warn")
        sleep(SHORT_SECONDS)
