# Decisions (ADR log)

Short, newest last. Format: date, decision, why.

## ADR-001: Repo layout mirrors the game's scripts folder by role

- Date: 2026-10-17
- Decision: game-facing code lives under `scripts/`. `scripts/main/` holds per-machine programs, `scripts/libs/` holds shared Libraries, `scripts/probes/` holds probe scripts. `tests/` holds pytest and `tests/harness/`.
- Why: the game's scripts folder is in AppData, outside this repo. It also gets regenerated files (stubs, workspace, logs) that must not be committed. Keeping our code in `scripts/` lets a later sync step copy only our files into the game.

## ADR-002: The game's scripts folder is not the repo root

- Date: 2026-10-17
- Decision: the repo does not replace the game folder. Sync to the game folder is a separate, explicit step that needs owner approval before it writes outside the repo.
- Why: the game folder holds generated files and the save. Pointing git at it would expose saves and logs to the repo.

## ADR-003: Game names map to repo files by role

- Date: 2026-10-17
- Decision: a machine script `scanner_1` is `scripts/main/scanner_1.py`. A Library `foo` is `scripts/libs/foo.py`, which the game reads as `lib/foo.py`.
- Why: matches the game's own naming so the game and the repo agree on names.

## ADR-004: Pure logic in plain functions, game calls only in an adapter

- Date: 2026-10-17
- Decision: each script keeps decisions in pure functions with no game calls. Only a thin adapter touches the game API. Tests exercise the pure functions and the adapter against the fake game in `tests/harness/`.
- Why: the game only runs inside the game. Pure logic can be tested under CPython; adapters are small enough to check by reading and by the in-game checklist.

## ADR-005: Tests load scripts with exec and injected fakes

- Date: 2026-10-17
- Decision: `tests/harness/fake_game.py` builds a restricted `__builtins__` dict containing only the names we implement. Scripts are compiled and `exec`ed with that dict. Any other name raises `NameError`.
- Why: the game's language is not CPython, so we cannot import scripts directly. A restricted builtins dict makes gaps in our API knowledge fail as test errors, not silent passes. It also stops scripts quietly relying on CPython builtins the game may lack.

## ADR-006: `tasks.ps1` instead of `make`

- Date: 2026-10-17
- Decision: task runner is `tasks.ps1`, run with `pwsh -File tasks.ps1 check`. CI runs the same file.
- Why: `make` is not installed on the dev machine (Windows 11). One runner avoids drift between local and CI.

## ADR-007: Hook via `.githooks/`, enabled by git config

- Date: 2026-10-17
- Decision: pre-commit hook lives in `.githooks/pre-commit` and runs `tasks.ps1 check`. Enable once with `git config core.hooksPath .githooks`.
- Why: no Python-based hook manager needed; one config command, as requested.

## ADR-008: Ruff config lives at the repo root

- Date: 2026-10-17
- Decision: `ruff.toml` is conservative (line length 100, selected rule groups E F W B UP SIM I). The game's own Ruff is not used because no generated Ruff config was found in the game folder.
- Why: the game applies a `ruff.toml` only from its scripts folder or above, so the repo config governs repo runs only. Known game-vs-Ruff syntax differences go in api-notes.

## ADR-009: Sync is one-way, hash-guarded, and never overwrites game edits

- Date: 2026-10-17
- Decision: `tools/sync_to_game.py` copies `scripts/main/*.py` to the game root and `scripts/libs/*.py` to `lib/`. It records the sha256 of each file it writes in `.sync-state.json` (gitignored). A game file that differs from that record is a conflict and is never overwritten. Protected names (`boot.py`, `user_stubs.py`, generated stubs and JSON, `logs/`, `.vscode/`, `.zed/`) are refused. `apply` refuses to run while conflicts exist unless `--skip-conflicts` is given. Dry run is the default.
- Why: the game writes in-game edits back to disk, so a plain copy would silently discard the owner's changes. Hash state tells "we changed it" apart from "the owner changed it".

## ADR-010: Game reference is our own short extracts, not a copy of the manual

- Date: 2026-10-17
- Decision: facts from the owner's in-game DOCS manual go into `docs/game/*.md` as short tables and notes, tagged VERIFIED (docs) with the build id. The full manual is not copied into the repo. Sections not yet needed stay listed as "not yet extracted".
- Why: the manual is about 1.7 MB and is the owner's material. Our notes stay small, and each fact can be traced to a section of the manual.

## ADR-011: Game-folder writes wait for the owner's tutorial

- Date: 2026-10-17
- Decision: no writes to the game folder (scripts, sync apply) until the owner says the in-game tutorial is complete. Read-only status checks are allowed.
- Why: the owner is partway through a fresh game. Our scripts would change tutorial state and could break the owner's own experiments.

## ADR-012: Owner-requested edits use a "Help me" marker; pulls go to review

- Date: 2026-10-17
- Decision: the owner names a script and writes `Help me` on line 1 of its game file. A file whose only content is that marker is treated as a request and may be replaced by sync. Any other owner code under the marker is a normal conflict. Game-side edits to files we wrote come back with `tasks.ps1 pull`, into `.sync-pull/`, never into the repo directly. `--only NAME` limits plan, apply and pull to one script.
- Why: the manual says the game keeps both versions when files collide and never overwrites an edited in-game script. A one-line marker is an explicit owner instruction, so it is safe to act on; anything else is left for review.

## ADR-013: Contract scripts are self-contained until Shared Library is researched

- Date: 2026-10-17
- Decision: `scripts/contracts/relay_hack.py` has no imports. It carries a copy of the solver from `scripts/libs/relay_hack.py`. Tests check the copy gives the right code on the same inputs.
- Why: the game raised `RuntimeError: Shared Library not yet researched` on any import from `lib/`. Contract scripts cannot wait for that research. Revisit when Shared Library is unlocked and move contract scripts back to imports.

## ADR-015: Biology scripts are self-contained; one sample per specimen

- Date: 2026-10-17
- Decision: each Bio script imports nothing (ADR-014). The Lab discards a specimen after a successful extract, treating each specimen as one sample. This is an assumption; the manual does not say a specimen is used up.
- Why: lib imports are blocked until Shared Library research. Discarding after extract frees the chamber, so the collector can refill it. Keeping the specimen would extract repeatedly and spend reagents with no stop condition.

## ADR-014: Machine scripts are self-contained too (extends ADR-013)

- Date: 2026-10-17
- Decision: `solar_1.py` carries its own copy of the tilt search and imports nothing. The power monitor (`harvester_1.py`) imports `lib/power_status` and must get the same treatment before its L3 run.
- Why: any `lib/` import needs Shared Library research, which the save lacks. The first machine script that imports from `lib/` will fail the same way the relay contract did.

## ADR-016: Power monitor is self-contained like the other machine scripts

- Date: 2026-10-17
- Decision: `harvester_1.py` carries a copy of the `power_status` rules and imports nothing. `scripts/libs/power_status.py` remains the tested source. Parity tests compare the copy's messages with the library's.
- Why: its import from `lib/` would fail without Shared Library research, the same blocker that stopped the relay contract.

## ADR-017: Harvester owns its slot; power monitor is parked

- Date: 2026-10-17
- Decision: `harvester_1.py` now controls the harvester. The power monitor moves to `scripts/parked/power_monitor.py`, which the sync tool does not copy. It returns once a free machine slot is chosen.
- Why: the owner asked for the harvester script on this slot. The monitor's tests still run against the parked copy.

## ADR-018: Sync compares line-ending-normalised content

- Date: 2026-10-17
- Decision: the sync tool normalises CRLF to LF before hashing, comparing and writing. Repo files can have CRLF from Windows text writes. Game files have LF.
- Why: byte comparison reported false conflicts (game and repo identical except for line endings). Re-based state entries were checked against game bytes before applying.

## ADR-019: Harvester reads its position and held item from the game

- Date: 2026-10-17
- Decision: `harvester_1.py` calls `self.get_position()` and `self.get_held()` every pass instead of assuming E13 or tracking moves. A held item is stored first.
- Why: a new save, or a later game point, need not start at E13. The manual gives both methods, and the held-slot check is its documented first step for a collect loop.

## ADR-020: Scanner follows the harvester; scans the nearest unscanned sector

- Date: 2026-10-17
- Decision: `scanner_1.py` centres on the harvester's current sector and scans the nearest of the 192 sectors it has not yet scanned in this sweep. Once all are done it waits one world hour and starts again. This widens the scan outward as nearby sectors are cleared, so new items keep appearing.
- Why: a fixed E13 sweep stops giving the harvester new targets once the nearby items are collected. The harvester only collects scanned items.

## ADR-021: Scanner scans the whole grid once per pass and saves a map (supersedes ADR-020)

- Date: 2026-10-17
- Decision: `scanner_1.py` runs a snake pass over all 192 sectors from base, saves the results to the Data Archive as `scanner.map` (status, name, value per sector) at the end of each row, and repeats each world hour. The scanner does not move, so the scan costs no harvester heat.
- Why: the scanner's self.scan is a base-side action (manual: scanner_1). A full map lets the harvester plan routes by heat and battery, which a nearest-first scan cannot do. ADR-020 is superseded.

## ADR-022: Harvester plans trips by heat, not distance

- Date: 2026-10-17
- Decision: `harvester_1.py` runs a shortest-path search over the 8x24 grid each pass. Entering an item sector costs 1 heat, anything else 7. Items are ranked by (path heat, steps). A trip is taken only if heat stays under HOT_HEAT. Otherwise the harvester cools first. There is no battery model: the owner confirmed the harvester has no battery.
- Why: heat is the only harvester budget in the manual, and the scanner map gives the item locations. Ranking by heat avoids empty cells where a detour through items is possible.
