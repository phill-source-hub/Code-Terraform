# Contract: Underground Data Tablet (`data_tablet`)

Source: owner-supplied briefing text for this contract (build `fe9a45c`). Tag: **VERIFIED (docs)** for the briefing facts below. Probe ordering and grid size beyond the briefing are UNVERIFIED until the in-game checklist passes.

## Briefing (short form)

- 30x30 grid of characters. Most cells are noise. Some cells form a hidden message.
- `tablet.probe(row, col)` returns `ProbeResult` with `.char` and `.distance` (Manhattan distance to the nearest message cell). Distance 0 marks a message cell.
- `tablet.rows` and `tablet.cols` give the grid size.
- `row` and `col` must be whole numbers inside the grid. Wrong types raise `TypeError`; fractional or out-of-bounds values raise `ValueError`.
- Answer: read the distance-0 characters left to right, top to bottom, and transmit the string with the contract id.

## Calls used

| Call | Notes |
|------|-------|
| `self.contract.tablet` | the tablet object |
| `tablet.probe(row, col)` | returns `ProbeResult` (`.char`, `.distance`) |
| `tablet.rows`, `tablet.cols` | grid dimensions |
| `get_component("transmitter")`, `connect("earth")`, `transmit(self.contract.id, message)` | see `docs/game/contracts.md` |

## Open questions

- Whether `rows` and `cols` are properties (as used) or methods: check in game.
- Whether a probe on a message cell returns that cell's own character: check in game.
- Probe cost or time budget per call: not in the briefing.
