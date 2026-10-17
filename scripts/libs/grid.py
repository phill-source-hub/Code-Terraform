"""Sector grid and route search for the scanner and the harvester. No game calls here.

Where it runs: Library (game `lib/grid.py`). Imported by scanner_1 and harvester_1.
Grid (manual, scanner_1): rows A-H map to 0-7, columns 1-24 map to 0-23. Base is E13.
Heat (manual, Harvester): stepping onto an item sector costs ITEM_STEP_HEAT, onto any other
    sector EMPTY_STEP_HEAT. A collected or never-scanned sector counts as empty.
API facts relied on: none. Callers pass plain strings and tuples.
"""

import heapq

ROWS = 8
COLS = 24
ITEM_STEP_HEAT = 1
EMPTY_STEP_HEAT = 7

# Cardinal neighbours only. The harvester moves one cell per call (manual, Harvester).
_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def sector_id(row: int, col: int) -> str:
    """Sector name for a zero-based grid cell, e.g. (4, 12) -> "E13"."""
    return chr(65 + row) + str(col + 1)


def parse_sector(name: str) -> tuple[int, int]:
    """Zero-based (row, col) for a sector name, the inverse of sector_id."""
    return ord(name[0]) - 65, int(name[1:]) - 1


def snake_order() -> list[tuple[str, bool]]:
    """Every sector in boustrophedon order, paired with whether it ends its row.

    Row A runs left to right, row B right to left, and so on. The row-end flag lets a caller
    save at the end of each row.
    """
    order = []
    for row in range(ROWS):
        cols = list(range(COLS)) if row % 2 == 0 else list(range(COLS - 1, -1, -1))
        for index, col in enumerate(cols):
            order.append((sector_id(row, col), index == len(cols) - 1))
    return order


def plan_routes(start, items):
    """Cheapest (heat, steps) to every cell from start, and the first step toward each.

    Dijkstra over the grid with a lexicographic cost, so equal heat prefers fewer steps.
    `items` is the list of sector names that cost ITEM_STEP_HEAT to enter. Returns
    (best, first): best maps (row, col) to (heat, steps); first maps (row, col) to the first
    cell to step onto on the way there, or None for the start cell itself.
    """
    best = {start: (0, 0)}
    first = {start: None}
    frontier = [(0, 0, start)]
    while frontier:
        heat, steps, cell = heapq.heappop(frontier)
        # Stale entry: a cheaper route to this cell was pushed after this one.
        if (heat, steps) != best[cell]:
            continue
        for dr, dc in _STEPS:
            nr = cell[0] + dr
            nc = cell[1] + dc
            if nr < 0 or nr >= ROWS or nc < 0 or nc >= COLS:
                continue
            neighbour = (nr, nc)
            name = sector_id(nr, nc)
            step_heat = ITEM_STEP_HEAT if name in items else EMPTY_STEP_HEAT
            cost = (heat + step_heat, steps + 1)
            if neighbour not in best or cost < best[neighbour]:
                best[neighbour] = cost
                first[neighbour] = neighbour if cell == start else first[cell]
                heapq.heappush(frontier, (cost[0], cost[1], neighbour))
    return best, first
