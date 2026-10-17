# Backlog

Items deferred on purpose. Each one names the trigger that makes it active.

## B-001: Save the scanner map to the Data Archive

- Trigger: Data Archive research unlocked in game (`get_component("notebook")` stops returning `None`).
- Status: code already in place. `scripts/main/scanner_1.py` calls `notebook.set("scanner.map", ...)` at the end of each row. Until unlock, the save is skipped and the scan still runs.
- To do when unlocked:
  1. Run `scanner_1` through one full pass. Confirm `scanner.map` appears in Computer > Data Archive with 192 entries.
  2. Confirm a `set` status is `ok`. Any other status shows as a `map save ...` warning in the status bar.
  3. Add a reader to `harvester_1.py`: if the live scanner snapshot is empty after a game load, load `scanner.map` from the archive and plan from it. The reader must stay self-contained (ADR-014).
  4. Add a test for the reader, using the fake Data Archive in the harness.
  5. Add an in-game checklist entry (SC-002) for the save and reload check.
- Notes: the Data Archive stores a copy and requires JSON-safe values (manual, Data Archive). The map is about 192 small dicts, well inside the 16,384-node limit.
