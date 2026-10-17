"""Harvester: collect scanned items, choosing each trip by heat cost, then store them in Inventory.

Where it runs: machine script slot `harvester_1` (self = this harvester). The harvester has no
    battery to manage; heat is its only budget (manual, Harvester: no battery is listed).
Imports the shared `grid` Library for sector names and the heat route search (ADR-025), and
    `trip_log` for the sectors already visited in this scan pass.
Visited log: kept in the Data Archive as `harvester.done`, so a game reload does not revisit
    sectors. It restarts whenever `scanner.pass` changes, because a new map can hold new items
    (ADR-026, backlog B-004). Without Data Archive research the log lives only in this run.
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
Signal Bus (docs/game/signal-bus.md, optional): takes a job from `jobs.collect` when it is reachable
    this pass; broadcasts `status.harvester_1` with its heat each pass; reads the scanner's
    `scan.ready` pass number. Without Signal Bus research the script runs as before.
API facts relied on (docs/game/harvester.md): self.get_position, self.get_held, self.get_heat,
    self.move, self.collect, self.store, get_component("scanner_1").get_scanned(),
    get_component("clock"), set_status, print, sleep. Signal Bus: comms.pending, receive,
    broadcast, latest (docs/game/signal-bus.md).
"""

from grid import parse_sector, plan_routes, sector_id
from job_queue import pick_job
from trip_log import is_done, mark_done, reconcile

HOT_HEAT = 80
SHORT_SECONDS = 5
JOB_CHANNEL = "jobs.collect"


scanner = get_component("scanner_1")
clock = get_component("clock")
cool_seconds = 3600
if clock is not None:
    cool_seconds = clock.real_seconds_per_hour()

notebook = get_component("notebook")
comms = get_component("comms")


def archive_pass(archive):
    if archive is None:
        return 0
    return archive.get("scanner.pass", 0)


def current_pass(archive, bus):
    # The scanner announces each finished pass on the bus, which works without Data Archive.
    if bus is not None:
        announced = bus.latest("scan.ready")
        if isinstance(announced, int):
            return announced
    return archive_pass(archive)


def take_job(bus, allowed):
    # Non-blocking: `wait` would stop the planner until a job arrives, so pending/receive is used.
    if bus is None:
        return None
    entries = [(message.id, message.value) for message in bus.pending(JOB_CHANNEL)]
    picked = pick_job(entries, allowed)
    if picked is None:
        return None
    received = bus.receive(JOB_CHANNEL, picked)
    if received.status == "ok":
        return received.packet.value
    return None


def report(bus, heat):
    if bus is not None:
        bus.broadcast("status.harvester_1", {"heat": heat})


def stored_log(archive):
    if archive is None:
        return None
    return archive.get("harvester.done", None)


def save_log(archive, log):
    # Saved after every change so a reload resumes from the last sector marked, not the start.
    if archive is not None:
        saved = archive.set("harvester.done", log)
        if saved.status != "ok":
            set_status("done save " + saved.status, "warn")
    return log


trip_log = reconcile(stored_log(notebook), current_pass(notebook, comms))

while True:
    report(comms, self.get_heat())
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

    trip_log = reconcile(trip_log, current_pass(notebook, comms))
    position = parse_sector(self.get_position())
    snapshot = scanner.get_scanned()
    items = [
        name for name in snapshot if snapshot[name].status == "ok" and not is_done(trip_log, name)
    ]
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

    # A queued job that is reachable this pass beats the planner's own pick (queue order).
    job = take_job(comms, [name for _, _, name in affordable])
    target_name = job if job is not None else min(affordable)[2]
    target = parse_sector(target_name)

    if position == target:
        pickup = self.collect()
        if pickup.status == "ok":
            trip_log = save_log(notebook, mark_done(trip_log, target_name))
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
            trip_log = save_log(notebook, mark_done(trip_log, target_name))
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
        trip_log = save_log(notebook, mark_done(trip_log, target_name))
        set_status("move " + moved.status + " to " + target_name, "warn")
        sleep(SHORT_SECONDS)
