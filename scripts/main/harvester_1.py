"""Harvester: collect scanned items one at a time, nearest first, and store them in Inventory.

Where it runs: machine script slot `harvester_1` (self = this harvester). The harvester has its
    own heat budget and does not draw from the base battery.
Self-contained on purpose (ADR-014): no imports.
Position: read from the game every pass with self.get_position(). Nothing is assumed about the
    start cell, because a new save or a later point in the game may not start at E13.
Held item: read with self.get_held() first, every pass. A held item is stored before anything
    else (the manual's first line of a collect loop).
Loop, one step per pass (manual: harvester_1, "start with one nearby scanned item"):
    1. cool down if heat is at or above HOT_HEAT (sleep one world hour);
    2. store any held item;
    3. read the scanner snapshot and pick the nearest "ok" item not yet collected;
    4. if standing on it, collect, then store; otherwise move one cardinal cell toward it.
Failure: busy or moving statuses wait SHORT_SECONDS. A refused move (invalid, too_far) drops the
    target. A full inventory waits. Every blocked path shows a status and sleeps.
API facts relied on (docs/game/harvester.md): self.get_position, self.get_held, self.get_heat,
    self.move, self.collect, self.store, get_component("scanner_1").get_scanned(),
    get_component("clock"), set_status, print, sleep.
"""

HOT_HEAT = 80
SHORT_SECONDS = 5


def sector_id(row, col):
    return chr(65 + row) + str(col + 1)


def parse_sector(name):
    return ord(name[0]) - 65, int(name[1:]) - 1


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def next_step(position, target):
    row, col = position
    if row != target[0]:
        return (row + (1 if target[0] > row else -1), col)
    return (row, col + (1 if target[1] > col else -1))


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
            print("stored " + str(stored.item_id) + " (was held)")
        else:
            set_status("store " + stored.status, "warn")
            sleep(SHORT_SECONDS)
        continue

    position = parse_sector(self.get_position())
    snapshot = scanner.get_scanned()
    candidates = [name for name in snapshot if snapshot[name].status == "ok" and name not in done]
    if not candidates:
        set_status("no items to collect", "info")
        sleep(SHORT_SECONDS * 12)
        continue

    target_name = min(candidates, key=lambda name: distance(position, parse_sector(name)))
    target = parse_sector(target_name)

    if position == target:
        pickup = self.collect()
        if pickup.status == "ok":
            done.append(target_name)
            stored = self.store()
            if stored.status == "ok":
                print("stored " + str(stored.item_id) + " from " + target_name)
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

    step = next_step(position, target)
    moved = self.move(sector_id(step[0], step[1]))
    if moved.status == "overheated":
        sleep(cool_seconds)
    elif moved.status in ("moving", "busy"):
        sleep(SHORT_SECONDS)
    elif moved.status not in ("ok", "already_here"):
        done.append(target_name)
        set_status("move " + moved.status + " to " + target_name, "warn")
        sleep(SHORT_SECONDS)
