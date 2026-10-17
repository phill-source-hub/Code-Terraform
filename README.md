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
| `scripts/templates/` | one template per controller shared by several slots; `tools/render_slots.py` writes `scripts/main/<slot>.py` from it (ADR-027). Edit the template, then run `python tools/render_slots.py` |
| `scripts/contracts/` | contract scripts (game root) |
| `scripts/automations/` | Automations (game: Ship Computer > Automations). Not synced: paste the file into a new Automation in game |
| `scripts/probes/` | probe scripts that check UNVERIFIED API facts |
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
| bio_collector_1 | Explore nearest uncataloged fragment, else one the order needs | machine `bio_collector_1` | L1+L2 pass, L3 pending |
| bio_lab_1 | Analyze specimen, stage reagents from Inventory, extract, ship sample | machine `bio_lab_1` (home base) | L1+L2 pass, L3 pending |
| bio_exchange_1 | Fill Bio Order from Inventory samples (home base) | machine `bio_exchange_1` (home base) | L1+L2 pass, L3 pending |
| o2gen_1 | Intake CO2/10, dump waste only in 50-60, last resort at 90 | machine `o2gen_1` (Mk I) | L1+L2 pass, L3 pending |
| pressure_1 / pressure_2 | Sync once per sweep inside the open window | machines `pressure_1`, `pressure_2` (Mk I) | L1+L2 pass, L3 pending |
| solar_1 / solar_2 (`solar_tracker`) | Tilt = 90 - sun elevation; imports the `solar_tracker` Library | machines `solar_1`, `solar_2` (Solar Generator) | solar_1 L3 pass (S-001); lib import L3 pending |
| relay_hack (contract) | Orbital Relay Hack; imports the `relay_hack` Library | contract `relay_hack` | Done (C-001 PASS); lib import L3 pending |
| xenogenetics (contract) | Transmit samples not in Earth reference | contract `xenogenetics` | Done (X-001 PASS) |
| corrupted_archive (contract) | Pair matching words in 10x10 grid | contract `corrupted_archive` | Done (X-002 PASS) |
| terminal_breach (contract) | Crack a 15-digit passcode (digits 1-5) from `.correct` feedback, transmit it | contract `terminal_breach` | Done (X-004 PASS) |
| data_tablet (contract) | Read distance-0 probe cells of a 30x30 tablet, transmit the message | contract `data_tablet` | Done (X-003 PASS) |
| probe_thermometer (`scripts/probes/`) | P-001 probe: version, component lookup, thermometer read | Run Script in Game, one-off | Done (P-001 PASS) |

Status values: Draft, L1+L2 pass, L3 pending, Done.

### Installing an Automation

`tools/sync_to_game.py` copies only `scripts/main/` and `scripts/libs/`. To run `scripts/automations/*.py`:

1. In game, open Ship Computer > Automations and click **+ New Automation**.
2. Paste the file's contents into its editor and save.
3. Needs Automations research. base_watch also needs Signal Bus research for heartbeats and alerts (it still reports power without it).

Where the game stores automation files on disk is UNVERIFIED, so this stays a manual paste until it is checked.

## Limits

- Game API facts are tagged VERIFIED or UNVERIFIED in `docs/api-notes.md`. Only stub-declared shapes are VERIFIED so far; behaviour is UNVERIFIED until checked in game.
- Tests run under CPython against a fake. Passing tests do not prove the game behaves the same; the in-game checklist does that.

## License

GPL-3.0. See [LICENSE](LICENSE).
