# Code-Terraform

Scripts for the game **Code: Terraform** (Steam 868160, by AppsMafia). The game runs its own Python-like language, not CPython, so this repo has a test harness that fakes the in-game API.

## Set up the game's External Editor

1. In the game: Settings > Editor > External Editor > **Set Up VS Code** (or PyCharm / Zed, see the game's `CODE-TERRAFORM-IDE.txt`).
2. The game keeps its own scripts folder at `%APPDATA%\io.codeterraform.game\save_mvcjaxut_26ndfi_scripts` (this save). That folder holds generated files, saves and logs. It is **not** this repo.
3. Scripts in this repo are copied into that folder by `tools/sync_to_game.py`. Each `apply` needs your go-ahead (ADR-009, ADR-011).

## Set up this repo

Requires Windows PowerShell or PowerShell 7, Python 3.12 and git.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
git config core.hooksPath .githooks   # enables the pre-commit check, once per clone
```

## Sync to the game folder

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 sync     # dry run: shows what would be copied
powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 status   # read-only: game warnings, errors, script status
python tools/sync_to_game.py apply                                      # writes to the game folder (your go-ahead each run)
```

`apply` writes only our files. It never overwrites a game file that changed since our last sync (see ADR-009). Game files it refuses are listed; resolve them by hand. The in-game tutorial is complete (ADR-011, lifted 2026-10-17).

## Game reference

Extracts from the in-game DOCS manual (build `fe9a45c`) are in [docs/game/](docs/game/README.md). The full manual is a local, git-ignored copy in `docs/game/manual/` (ADR-023).

## Run the checks

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 check    # format + lint + tests
powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 test     # tests only
powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 format   # apply formatting
```

CI runs `check` on every push and pull request (`.github/workflows/ci.yml`).

## Layout

| Path | Contents |
|------|----------|
| `scripts/main/` | per-machine programs (file name = machine id) |
| `scripts/libs/` | shared Libraries (game `lib/`) |
| `scripts/main/` (solar, o2gen, pressure) | one file per controller, copied to each slot; the `_1` file is the source. Copy it to add a slot (ADR-033, ADR-034). `tests/test_controller_copies.py` checks the copies match |
| `scripts/contracts/` | contract scripts (game root) |
| `scripts/automations/` | Automations (game: Ship Computer > Automations). Not synced: paste the file into a new Automation in game |
| `scripts/probes/` | probe scripts that check UNVERIFIED API facts |
| `scripts/cards/` | Control Room card scripts (dashboards). Not synced: paste each file into a new card in the Control Room |
| `tests/` | pytest suite; `tests/harness/` is the fake game API |
| `docs/` | `api-notes.md`, `decisions.md`, `backlog.md`, `in-game-test-log.md`, `specs/`, `game/` (extracts; `game/manual/` is local only) |
| `.claude/agents/` | Claude Code subagents used for this project |

## Script index

| Name | Purpose | Where it runs | Status |
|------|---------|---------------|--------|
| base_watch (Automation, `scripts/automations/base_watch.py`) | Warn on power deficit, low battery, and silent or missing machine heartbeats; broadcasts `base.alerts`. Replaces the parked power monitor (ADR-029) | Automation, no machine slot | Unit tests only; in-game checklist pending |
| scanner_1 | Snake-scan all 192 sectors, save map to Data Archive (once researched), repeat hourly; imports `grid` | machine `scanner_1` | L1+L2 pass, L3 pending |
| harvester_1 | Plan heat-cheapest trips to scanned items, collect and store; imports `grid` | machine `harvester_1` | L1+L2 pass, L3 pending |
| grid (Library) | Sector names, snake order, heat route search for scanner and harvester | `scripts/libs/grid.py` (game `lib/grid.py`) | Unit tests only; L3 pending |
| bio_collector_1 | Collect fragments that open Bio Orders still need (multi-item, net of stock and in-flight), else explore | machine `bio_collector_1` | L1+L2 pass, L3 pending |
| bio_lab_1 | Analyze specimen, buy missing reagents from the Shop, stage and load them, extract, ship sample | machine `bio_lab_1` (home base) | L1+L2 pass, L3 pending |
| bio_exchange_1 | Fill open Bio Orders (several required fragments) from Inventory samples; returns surplus to Inventory (home base) | machine `bio_exchange_1` (home base) | L1+L2 pass, L3 pending |
| o2gen_1 | Intake CO2/10, dump waste only in 50-60, last resort at 90 | machine `o2gen_1` (Mk I) | L1+L2 pass, L3 pending |
| pressure_1 / pressure_2 | Sync once per sweep inside the open window | machines `pressure_1`, `pressure_2` (Mk I) | L1+L2 pass, L3 pending |
| heater_1 | Scan 0.1-10.0 once per thermal state for the power that reads 100%, then hold it (ADR-035) | machine `heater_1` (Mk I Heat Generator) | Unit tests only; L3 pending (H-001 to H-005) |
| solar_1 / solar_2 (`solar_tracker`) | Tilt = 90 - sun elevation; imports the `solar_tracker` Library | machines `solar_1`, `solar_2` (Solar Generator) | solar_1 L3 pass (S-001); lib import L3 pending |
| relay_hack (contract) | Orbital Relay Hack; imports the `relay_solver` Library (ADR-030) | contract `relay_hack` | Done (C-001 PASS); lib import L3 pending |
| xenogenetics (contract) | Transmit samples not in Earth reference | contract `xenogenetics` | Done (X-001 PASS) |
| corrupted_archive (contract) | Pair matching words in 10x10 grid | contract `corrupted_archive` | Done (X-002 PASS) |
| terminal_breach (contract) | Crack a 15-digit passcode (digits 1-5) from `.correct` feedback, transmit it | contract `terminal_breach` | Done (X-004 PASS) |
| data_tablet (contract) | Read distance-0 probe cells of a 30x30 tablet, transmit the message | contract `data_tablet` | Done (X-003 PASS) |
| probe_thermometer (`scripts/probes/`) | P-001 probe: version, component lookup, thermometer read | Run Script in Game, one-off | Done (P-001 PASS) |
| control_room (Library, `scripts/libs/control_room.py`) | Runway, colour, progress, channel and alert logic for the Control Room cards | `lib/control_room.py` | Unit tests only; L3 pending (D-001 to D-005) |
| D2 power runway (card, `scripts/cards/d2_power_runway.py`) | One gauge per power grid with hours of storage left at the deficit | Control Room card, 2x1 | Unit tests only; L3 pending (D-001) |
| D3 fleet board (card, `scripts/cards/d3_fleet_board.py`) | Vehicles and drones: status dot, status, battery or oil bar; problems first | Control Room card, 2x1 | Unit tests only; L3 pending (D-002) |
| D6 Earth Orders (card, `scripts/cards/d6_earth_orders.py`) | Current order progress and upcoming orders with rewards | Control Room card, 2x1 | Unit tests only; L3 pending (D-003) |
| D9 Signal Bus monitor (card, `scripts/cards/d9_signal_bus.py`) | Pending messages and latest broadcast on a typed channel | Control Room card, 2x1 | Unit tests only; L3 pending (D-004) |
| D1 base overview (card, `scripts/cards/d1_base_overview.py`) | Power, atmosphere, fleet health, top orders and an alert strip | Control Room card, 2x2 | Unit tests only; L3 pending (D-005) |

Status values: Draft, L1+L2 pass, L3 pending, Done.

### Installing a Control Room card

Each file in `scripts/cards/` is one card's script. Open the Control Room, click + New Card, pick the size in the file's header, and paste the file in. Cards import `control_room`, which syncs to game `lib/` with the Libraries (owner go-ahead, see `tools/sync_to_game.py`). Until the Library is in game, a card shows an import error.

### Installing an Automation

`tools/sync_to_game.py` copies `scripts/main/`, `scripts/contracts/`, `scripts/libs/`, and the automations listed in `AUTOMATION_TARGETS`. `base_watch.py` syncs to the game root as `automation_1.py`, the name the game index uses for automations. Needs Automations research. base_watch also needs Signal Bus research for heartbeats and alerts; it still reports power without it.

Unmapped automation files are not synced. Add a name to `AUTOMATION_TARGETS` to sync one.

## Limits

- Game API facts are tagged VERIFIED or UNVERIFIED in `docs/api-notes.md`. Only stub-declared shapes are VERIFIED so far; behaviour is UNVERIFIED until checked in game.
- Tests run under CPython against a fake. Passing tests do not prove the game behaves the same; the in-game checklist does that.

## License

GPL-3.0. See [LICENSE](LICENSE).
