# Code: Terraform API notes

Index and short facts. Detailed per-system extracts live in `docs/game/` (see its README). Every fact is tagged:

- **VERIFIED (docs)**: copied or summarised from the in-game DOCS manual, build `fe9a45c`, supplied by the owner.
- **VERIFIED (stub)**: seen in the game-generated `__builtins__.pyi` stub (signature and/or docstring). Shape only, not in-game behaviour.
- **VERIFIED (ingame)**: a script ran in game and the result was checked against `docs/in-game-test-log.md`. None yet.
- **UNVERIFIED**: anything else. Do not write code that depends on it without a probe.

The game's DOCS manual is the main reference. Stubs are generated per game build and sit in the game folder, not in the repo. After a game update, re-check signatures and bump the build id in `docs/game/README.md`.

## Index of extracted docs

| File | Covers | Status |
|------|--------|--------|
| `docs/game/language.md` | output, self/components, result contract, long-running scripts, exceptions, loops | extracted, partial (see its "not yet extracted" list) |
| `docs/game/libraries.md` | imports, Libraries, built-in modules, typing names | extracted |
| `docs/game/rover.md` | Rover, nav, sonar, drill, mount, status | extracted |
| `docs/game/power.md` | grids, power control, battery, battery charger, solar, vehicle charging | extracted |
| `docs/game/fabricator.md` | fabricator, recipes (sample), ports, transfer results, ItemStack | extracted |
| `docs/game/drone.md` | drones, fleet, drone service station | extracted |
| `docs/game/contracts.md` | contracts, transmitter, contract result statuses | extracted; 15 contract subtypes not yet |

## Language (headline facts)

- VERIFIED (docs): the language is Python-like. The interpreter gives time back to the game during `while` loops; `sleep()` is for deliberate pacing.
- VERIFIED (docs): `print`, `warn`, `debug` are the output channels. `debug` is hidden unless enabled.
- VERIFIED (docs): a world-changing command returns a result object with `.status` and `.message`. Never branch on `.message`. Result objects are truthy even when rejected.
- VERIFIED (docs): `from __builtins__ import X` binds a game type or builtin explicitly.
- VERIFIED (docs): a running script restarts from line one after a game load. Locals are lost.
- VERIFIED (stub): builtins `set_status`, `notify`, `sleep`, `get_component`, `get_game_version`, `print` exist with the signatures in the stub.
- VERIFIED (stub): `notify` duration is clamped to 0.5-30 s; `0` is sticky (docs say the same in the notify entry).
- VERIFIED (docs): `typing.TYPE_CHECKING` is `False` in the game. `typing.NamedTuple` runs.
- UNVERIFIED: whether `exec`, `eval`, `open`, `input` exist. The docs do not list them. Assume no.
- UNVERIFIED: `randint` inclusive or exclusive upper bound. Docs say `randint(min, max)`.

## Machines and components (headline facts)

- VERIFIED (docs): `get_component(id)` returns the component or `None`. IDs are case-sensitive and stable. Use ids in long-running scripts.
- VERIFIED (stub): every component has `.id` and `.type_id`.
- VERIFIED (docs): `power_control.set_powered(machine_id, on)` pauses or resumes that machine's scripts. Outcomes include `not_enough_power`.

## Known game-vs-Ruff difference (log evidence)

- VERIFIED (ingame log, 2026-10-17 15:46): the game reported `SyntaxError: invalid syntax at '/='` for an `oxygen_sensor.py` script at line 4. The owner's current file no longer contains `/=`, so the exact construct the game rejects is UNVERIFIED. Probe before relying on augmented assignment with `/=`.

## Probes

| Probe | Checks | Result |
|-------|--------|--------|
| `scripts/probes/probe_thermometer.py` (P-001) | version call, component lookup, thermometer read | not run yet |
