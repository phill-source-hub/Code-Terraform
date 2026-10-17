# Backlog

Items deferred on purpose. Each one names the trigger that makes it active.

## B-001: Save the scanner map to the Data Archive

- Trigger: Data Archive research unlocked in game (`get_component("notebook")` stops returning `None`). Research costs Terraform Index 70,000 (manual, Research page); Ship Computer (10,000) does not add it.
- Status: code already in place. `scripts/main/scanner_1.py` calls `notebook.set("scanner.map", ...)` at the end of each row. Until unlock, the save is skipped and the scan still runs.
- To do when unlocked:
  1. Run `scanner_1` through one full pass. Confirm `scanner.map` appears in Computer > Data Archive with 192 entries.
  2. Confirm a `set` status is `ok`. Any other status shows as a `map save ...` warning in the status bar.
  3. Add a reader to `harvester_1.py`: if the live scanner snapshot is empty after a game load, load `scanner.map` from the archive and plan from it. The reader may import a Library now that Shared Library is researched (see B-002).
  4. Add a test for the reader, using the fake Data Archive in the harness.
  5. Add an in-game checklist entry (SC-002) for the save and reload check.
- Notes: the Data Archive stores a copy and requires JSON-safe values (manual, Data Archive). The map is about 192 small dicts, well inside the 16,384-node limit.

## B-002: Replace self-contained copies with Library imports

- Trigger: Shared Library researched (done 2026-10-17) and an owner go-ahead for a game sync.
- Status: open.
- To do, in order: 1. Sync `scripts/libs/` first so `lib/` exists in the game. 2. `solar_1.py` and `solar_2.py` import `solar_tracker`. 3. `scripts/contracts/relay_hack.py` imports `relay_hack`. 4. `scripts/parked/power_monitor.py` imports `power_status` when it returns to a slot. 5. Delete the copy-parity tests (`tests/test_solar_copies.py`, the relay parity check in `tests/test_relay_hack_script.py`) and add a test that the game-style import resolves. 6. Log each change in `docs/in-game-test-log.md`.
- Notes: Libraries must not use `self` or `panel` (manual, Imports & Libraries).

## B-003: Shared grid helpers

- Trigger: after B-002.
- Status: open.
- To do: move `ROWS`, `COLS`, `sector_id`, `parse_sector` and `plan_routes` from `scanner_1.py` and `harvester_1.py` into `scripts/libs/grid.py`. Use `heapq` (a documented built-in) for the route search. Unit-test the route search directly.

## B-004: Harvester `done` list is never cleared

- Trigger: confirm in game whether scanned sectors refill (the manual does not say; see `docs/game/harvester.md`).
- Status: open. Possible bug.
- Problem: `harvester_1.py` adds each collected or empty sector to `done` and never removes it. If sectors refill or the map is re-saved, the harvester ignores them for the rest of the run.
- Fix options: clear `done` when the scanner map is re-saved, or key it by the save time.
