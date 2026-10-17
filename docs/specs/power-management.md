# Spec: power management

Status: draft. Owner to confirm scope before scripts are written.

## Goal

Keep the base's power supply steady: warn early, track the sun, and keep the battery charger fed. Each script is read-only unless marked otherwise.

## Scripts (in order)

1. **power_monitor** (exists, `harvester_1`). Read-only. Warns on a grid deficit or battery under 20%. L3 pending.
2. **solar_tracker** (solar generator `solar_1`). Writes tilt. Sets tilt = 90° − sun elevation (`clock.get_elevation()`, VERIFIED docs), clamped 0-90°. Samples every 1/12 world hour. Tilt resets to 90° when the script stops. Needs a Solar Generator (500 cr, VERIFIED docs).
3. **battery_charger_queue** (new, battery charger). Writes charge jobs. Queues each low cell with `charge(slot, target)`, skips full cells, reports queue state. Needs Battery Charger research (Oxygen 25) and purchase (1,500 cr, VERIFIED docs).

## Success criteria

- Each script runs without an error in the game log (`tasks.ps1 status`).
- Each script's checklist in `docs/in-game-test-log.md` passes.
- Logic lives in a Library or in a self-contained script, with unit tests (ADR-013 for contracts; Libraries for machines).

## Safety limits

- solar_tracker never writes tilt outside 0-90°.
- battery_charger_queue never cancels a job that is in progress (`stop()` only for cells the owner asks to release).
- No script powers a machine on or off. `power_control.set_powered` is out of scope.

## Open questions (owner)

- Which machine hosts solar_tracker and battery_charger_queue? Free slots: `bio_collector_1`, `bio_lab_1`, `bio_exchange_1` (unpowered), or a new machine.
- Solar tracker: sweep step size and sweep period. Not in the manual. Pick a default and tune in game.
- Do we want a power_monitor alert to stop the charger when storage is low? Not decided.

## API facts relied on

See `docs/game/power.md` (VERIFIED docs) and `docs/api-notes.md`. Behaviour of `set_tilt` and `charge` in game is UNVERIFIED until the checklists pass.
