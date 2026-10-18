# Game scripts inventory

Checked 2026-10-17 against the game folder `%APPDATA%\io.codeterraform.game\save_mvcjaxut_26ndfi_scripts` (read only). Each row says where the file is tracked and whether the game copy matches the repo. Code is not copied here; owner-written scripts are listed by name only.

## Tracked and matching the game

| Game file | Repo source | Notes |
|-----------|-------------|-------|
| `bio_collector_1.py`, `bio_exchange_1.py`, `bio_lab_1.py` | `scripts/main/` | same |
| `corrupted_archive.py`, `data_tablet.py`, `terminal_breach.py`, `xenogenetics.py` | `scripts/contracts/` | same |
| `pressure_1.py`, `pressure_2.py` | `scripts/main/` (copies of `pressure_1.py`, ADR-034) | same code; docstring-only change pending a sync |
| `scanner_1.py` | `scripts/main/` | same since the 2026-10-17 apply |
| `solar_4.py`, `solar_5.py` | `scripts/main/` (plain copies of `solar_1.py`, ADR-033) | Were `Help me` placeholders; replaced by the owner-approved sync on 2026-10-18. Now identical to `solar_1.py`; re-synced to the game 2026-10-18 (hash matches). |
| `lib/*.py` (7 files) | `scripts/libs/` | `power_status`, `relay_solver`, `solar_tracker`, `grid`, `trip_log`, `job_queue`, `base_watch` |

## Tracked, game copy differs (sync conflict, skipped)

| Game file | Repo source | State in game |
|-----------|-------------|---------------|
| `harvester_1.py` | `scripts/main/harvester_1.py` | Game holds the old power-monitor copy on this slot (ADR-017 era). Owner decision needed. |
| `o2gen_1.py` | `scripts/main/o2gen_1.py` (source, ADR-034) | Older version, no `sleep` (ADR-024 change not in game). |
| `relay_hack.py` | `scripts/contracts/relay_hack.py` | Older self-contained copy. |
| `solar_1.py`, `solar_2.py` | `scripts/main/` (generated) | Older self-contained copies. |
| `solar_3.py` | `scripts/main/solar_3.py` (generated, slot added 2026-10-17) | Copy of the solar code, docstring says `solar_2`. Not written by sync. |

## Tracked now, not yet in game

| Repo file | Game copy | Note |
|-----------|-----------|------|
| `scripts/main/o2gen_2.py`, `o2gen_3.py` | `o2gen_2.py`, `o2gen_3.py` exist | Older copies of the O2 controller. Sync reports conflict. |
| `scripts/main/pressure_3.py` | `pressure_3.py` exists | Copy of the pressure controller (same size as the game's pressure_1 copy). Sync reports conflict. |
| `scripts/automations/base_watch.py` | not a sync target | Paste by hand into an Automation (README). |
| `scripts/probes/probe_thermometer.py` | no file on disk | P-001 ran once; the file is gone from the game folder. |

## Game-managed or generated (not ours, left alone)

- `boot.py` (protected by sync; game writes it).
- `*.pyi` stubs (`__builtins__.pyi`, `builtins.pyi`, module stubs). Regenerated per game build.
- `user_stubs.py`, `pyrightconfig*.json`, `CODE-TERRAFORM-IDE.txt`, `codeterraform-*.json`, `.gitignore`, `.vscode/`, `.zed/`, `logs/`, `typeshed-LICENSE.txt`.

## Owner-written, tracked as copies (`scripts/owner/`, not synced)

Copies made by the owner's own hand, committed on the owner's request. Byte-identical to the game files on 2026-10-17. Not synced: the repo does not own them.

- `oxygen_sensor.py`: reads the oxygen sensor and calls `calibrate`. Named in the `/=` syntax note in `docs/api-notes.md`.
- `pressure_sensor.py`: reads the pressure sensor and calls `stabilize`.
- `planet_power.py`: calls `activate_power()`.
- `planet_sensors.py`: calls `activate_sensors()`.
- `uplink.py`: reads the thermometer and transmits `current_temperature` to Earth.

## In the game index but no file on disk

`codeterraform-scripts.json` lists these, with no `.py` file present: `rover_1`, `heater_1`, `charging_station_1`, `automation_1`. They are stale index entries or deleted scripts. Left alone.
