# Backlog

Items deferred on purpose. Each one names the trigger that makes it active.

## B-001: Save the scanner map to the Data Archive

- Trigger: Data Archive research unlocked in game (`get_component("notebook")` stops returning `None`). Research costs Terraform Index 70,000 (manual, Research page); Ship Computer (10,000) does not add it.
- Status: code on `feat/data-archive-persistence`. `scripts/main/scanner_1.py` saves `scanner.map` once per complete pass, then `scanner.pass` (ADR-026). Until unlock, the save is skipped and the scan still runs. Step 3 (harvester reads the map on reload) is not written yet.
- To do when unlocked:
  1. Run `scanner_1` through one full pass. Confirm `scanner.map` appears in Computer > Data Archive with 192 entries.
  2. Confirm a `set` status is `ok`. Any other status shows as a `map save ...` warning in the status bar.
  3. Add a reader to `harvester_1.py`: if the live scanner snapshot is empty after a game load, load `scanner.map` from the archive and plan from it. The reader may import a Library now that Shared Library is researched (see B-002).
  4. Add a test for the reader, using the fake Data Archive in the harness.
  5. Add an in-game checklist entry (SC-002) for the save and reload check.
- Notes: the Data Archive stores a copy and requires JSON-safe values (manual, Data Archive). The map is about 192 small dicts, well inside the 16,384-node limit.

## B-002: Replace self-contained copies with Library imports

- Trigger: Shared Library researched (done 2026-10-17) and an owner go-ahead for a game sync.
- Status: repo done on `refactor/shared-libs` (ADR-025). Not yet in game: needs the owner's go-ahead for `sync_to_game.py apply`, then the in-game checklist. The parked power monitor copy is removed by the Automation work, not migrated.
- To do, in order: 1. Sync `scripts/libs/` first so `lib/` exists in the game. 2. `solar_1.py` and `solar_2.py` import `solar_tracker`. 3. `scripts/contracts/relay_hack.py` imports `relay_hack`. 4. (Superseded by ADR-029: the parked power monitor is the base_watch Automation, which imports `power_status`.) 5. Delete the copy-parity tests (`tests/test_solar_copies.py`, the relay parity check in `tests/test_relay_hack_script.py`) and add a test that the game-style import resolves. 6. Log each change in `docs/in-game-test-log.md`.
- Notes: Libraries must not use `self` or `panel` (manual, Imports & Libraries).

## B-003: Shared grid helpers

- Trigger: after B-002.
- Status: repo done on `refactor/shared-libs`. `scripts/libs/grid.py` holds `ROWS`, `COLS`, `sector_id`, `parse_sector`, `snake_order` and `plan_routes` (heapq). Unit-tested in `tests/test_grid.py`. Game check pending with B-002.

## B-004: Harvester `done` list is never cleared

- Trigger: confirm in game whether scanned sectors refill (the manual does not say; see `docs/game/harvester.md`).
- Status: fixed on `feat/data-archive-persistence` (ADR-026). The visited log is `harvester.done` = {pass, sectors}, cleared when `scanner.pass` changes. It is also saved, so a reload resumes. Game check pending (needs Data Archive research).
- Problem (was): `harvester_1.py` added each collected or empty sector to `done` and never removed it. If sectors refilled or the map was re-saved, the harvester ignored them for the rest of the run.
