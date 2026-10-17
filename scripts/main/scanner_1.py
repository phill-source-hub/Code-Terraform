"""Scanner: sweep the sectors around base and report what is there.

Where it runs: machine script slot `scanner_1` (self = this scanner).
Self-contained on purpose (ADR-014): no imports.
Grid (manual, scanner_1): rows A-H map to 0-7, columns 1-24 map to 0-23. Base is E13.
Method: sweep the sectors within SCAN_RADIUS of base, nearest first, printing each result.
    Then wait one world-clock hour and sweep again (items may change; UNVERIFIED).
Results are kept in the scanner's snapshot (get_scanned), which bio and harvest scripts read.
Failure: a result status other than ok or empty is shown as a warning, and the sweep goes on.
API facts relied on (docs/game/harvester.md): self.scan(sector_id) -> ScanResult (.status,
    .message, .id, .name, .value); chr(); get_component("clock").real_seconds_per_hour();
    set_status, print, sleep.
"""

BASE_ROW = 4
BASE_COL = 12
SCAN_RADIUS = 1
ROWS = 8
COLS = 24


def sector_id(row, col):
    return chr(65 + row) + str(col + 1)


def sectors_around(row, col, radius):
    found = []
    for r in range(ROWS):
        for c in range(COLS):
            distance = abs(r - row) + abs(c - col)
            if distance <= radius:
                found.append((distance, sector_id(r, c)))
    found.sort()
    return [name for distance, name in found]


clock = get_component("clock")
sweep_seconds = 3600
if clock is not None:
    sweep_seconds = clock.real_seconds_per_hour()

while True:
    for name in sectors_around(BASE_ROW, BASE_COL, SCAN_RADIUS):
        result = self.scan(name)
        if result.status == "ok":
            print(name + ": " + result.name)
        elif result.status == "empty":
            print(name + ": empty")
        else:
            set_status(name + " " + result.status, "warn")
    set_status("sweep complete", "info")
    sleep(sweep_seconds)
