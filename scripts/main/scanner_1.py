"""Scanner: scan the nearest unscanned sector to the harvester, so new items keep appearing.

Where it runs: machine script slot `scanner_1` (self = this scanner).
Self-contained on purpose (ADR-014): no imports.
Grid (manual, scanner_1): rows A-H map to 0-7, columns 1-24 map to 0-23. Base is E13.
Centre: the harvester's current sector, read with get_component("harvester_1").get_position().
    The manual gives this as a plain read; if the harvester is missing, the centre is base (E13).
Method, one scan per pass: among the 192 sectors not yet scanned in this sweep, scan the one
    nearest the harvester. The search widens on its own as nearby sectors are done, so the
    scanner reaches new ground when the harvester has cleared its area.
When every sector has been scanned, the sweep starts again after one world-clock hour.
Results are kept in the scanner's snapshot (get_scanned), which the harvester reads.
Failure: a result status other than ok or empty is shown as a warning, and the sweep goes on.
API facts relied on (docs/game/harvester.md): self.scan(sector_id) -> ScanResult (.status,
    .message, .name); chr(); get_component("harvester_1").get_position();
    get_component("clock").real_seconds_per_hour(); set_status, print, sleep.
"""

BASE_ROW = 4
BASE_COL = 12
ROWS = 8
COLS = 24


def sector_id(row, col):
    return chr(65 + row) + str(col + 1)


def parse_sector(name):
    return ord(name[0]) - 65, int(name[1:]) - 1


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def all_sectors():
    return [sector_id(r, c) for r in range(ROWS) for c in range(COLS)]


harvester = get_component("harvester_1")
clock = get_component("clock")
sweep_seconds = 3600
if clock is not None:
    sweep_seconds = clock.real_seconds_per_hour()

scanned = []

while True:
    if harvester is not None:
        centre_name = harvester.get_position()
    else:
        centre_name = sector_id(BASE_ROW, BASE_COL)
    centre = parse_sector(centre_name)

    remaining = [name for name in all_sectors() if name not in scanned]
    if not remaining:
        set_status("grid scanned, starting again", "info")
        scanned = []
        sleep(sweep_seconds)
        continue

    name = min(remaining, key=lambda sector: distance(centre, parse_sector(sector)))
    result = self.scan(name)
    scanned.append(name)
    if result.status == "ok":
        print(name + ": " + result.name)
    elif result.status == "empty":
        print(name + ": empty")
    else:
        set_status(name + " " + result.status, "warn")
    set_status(str(len(scanned)) + " of 192 scanned, centre " + centre_name, "info")
