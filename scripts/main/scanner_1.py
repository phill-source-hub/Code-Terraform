"""Scanner: snake-scan the whole grid, save the results as a map, and repeat each world hour.

Where it runs: machine script slot `scanner_1` (self = this scanner).
Imports the shared `grid` Library for sector names and snake order (ADR-025).
Grid (manual, scanner_1): rows A-H map to 0-7, columns 1-24 map to 0-23. Base is E13.
    The scanner does not move. Scanning every sector from here costs no harvester heat or power.
Method: a snake (boustrophedon) pass. Row A runs left to right, row B right to left, and so on.
    Each result goes into a map: sector id -> {status, name, value}.
Saving: the map is written to the Data Archive under MAP_KEY (`notebook.set`) at the end of each
    row, so a stop part-way keeps what was scanned. The Data Archive needs its research. Without
    it the scanner still scans and the harvester still reads the scanner snapshot.
Repeat: the full grid is scanned again after one world-clock hour, so the map follows changes.
Failure: a result status other than ok or empty is shown as a warning, and the scan goes on.
    A failed save is shown as a warning. The scan goes on.
API facts relied on (docs/game/harvester.md and manual Data Archive): self.scan(sector_id) ->
    ScanResult (.status, .name, .value); get_component("notebook") (None until Data Archive
    research); notebook.set(key, value) -> ActionResult (.status, .message); chr(); get_component
    ("clock").real_seconds_per_hour(); set_status, print, sleep.
"""

from grid import snake_order

MAP_KEY = "scanner.map"

notebook = get_component("notebook")
clock = get_component("clock")
repeat_seconds = 3600
if clock is not None:
    repeat_seconds = clock.real_seconds_per_hour()

while True:
    grid_map = {}
    for name, row_end in snake_order():
        result = self.scan(name)
        grid_map[name] = {"status": result.status, "name": result.name, "value": result.value}
        if result.status == "ok":
            print(name + ": " + result.name)
        elif result.status != "empty":
            set_status(name + " " + result.status, "warn")
        if row_end and notebook is not None:
            saved = notebook.set(MAP_KEY, grid_map)
            if saved.status != "ok":
                set_status("map save " + saved.status + ": " + saved.message, "warn")
    set_status("map of " + str(len(grid_map)) + " sectors saved", "info")
    sleep(repeat_seconds)
