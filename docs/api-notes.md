# Code: Terraform API notes

Index and short facts. Detailed per-system extracts live in `docs/game/` (see its README). Every fact is tagged:

- **VERIFIED (docs)**: copied or summarised from the in-game DOCS manual, build `fe9a45c`, supplied by the owner.
- **VERIFIED (stub)**: seen in the game-generated `__builtins__.pyi` stub (signature and/or docstring). Shape only, not in-game behaviour.
- **VERIFIED (ingame)**: a script ran in game and the result was checked against `docs/in-game-test-log.md`. See "In-game evidence" below.
- **UNVERIFIED**: anything else. Do not write code that depends on it without a probe.

The game's DOCS manual is the main reference. Stubs are generated per game build and sit in the game folder, not in the repo. After a game update, re-check signatures and bump the build id in `docs/game/README.md`.

## Index of extracted docs

| File | Covers | Status |
|------|--------|--------|
| `docs/game/language.md` | output, self/components, result contract, long-running scripts, exceptions, loops | extracted, partial; rest in `docs/game/manual/` |
| `docs/game/libraries.md` | imports, Libraries, built-in modules, typing names | extracted |
| `docs/game/rover.md` | Rover, nav, sonar, drill, mount, status | extracted |
| `docs/game/power.md` | grids, power control, battery, battery charger, solar, vehicle charging | extracted |
| `docs/game/fabricator.md` | fabricator, recipes (sample), ports, transfer results, ItemStack | extracted |
| `docs/game/drone.md` | drones, fleet, drone service station | extracted |
| `docs/game/contracts.md` | contracts, transmitter, contract result statuses | extracted; subtype APIs in `docs/game/manual/` |
| `docs/game/contracts-terminal-breach.md` | Alien Terminal Breach | extracted; in-game PASS (X-004) |
| `docs/game/contracts-data-tablet.md` | Underground Data Tablet | extracted; in-game PASS (X-003) |
| `docs/game/manual/` | full in-game DOCS manual, split by section (local, git-ignored, ADR-023) | complete, build fe9a45c |

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
- UNVERIFIED: that `self` in a machine script is the generator and carries `.id`. The solar scripts rely on `self` for identity (ADR-033) and read no id. Check in game (S-001 row, 2026-10-18).
- VERIFIED (docs): `power_control.set_powered(machine_id, on)` pauses or resumes that machine's scripts. Outcomes include `not_enough_power`.

## In-game evidence (VERIFIED ingame)

- P-001 (2026-10-17): `get_game_version()`, `get_component("thermometer")`, `thermometer.type_id` and `Thermometer.get_value()` behave as the stub declares. Log in `docs/in-game-test-log.md`.
- Contracts C-001, X-001 to X-004 (2026-10-17): `get_component("transmitter")`, `connect("earth")` and `transmit(contract.id, answer)` return status `correct`, and the contract status becomes `completed`.
- X-003 and X-004: `tablet.rows`, `tablet.cols` and `terminal.length` are properties, and the `.correct` feedback rule held in game.
- S-001 (2026-10-17): tilt = 90 - sun elevation, using `clock.get_elevation()`, matches the output on the morning check.
- PX-001 runs 3 and 4 (2026-10-18, `scripts/probes/probe_control_room.py`): the Control Room widgets `card`, `draw_text`, `label`, `status_dot`, `progress_bar`, `button`, `switch`, `text_field`, `combo`, `draw_rect`, `draw_line`, `draw_circle` draw with the stub's argument order (`key` first on `button`, `switch`, `text_field`, `combo`). `set_text`/`get_text` and `set_switch`/`get_switch` round-trip. `mouse()` returns an object with `x` and `y`. Run 4 is the bus limit below. The `clicks()` and `persist` rows passed in run 3.

## Data Archive and research gates (VERIFIED docs, manual)

- Data Archive needs Data Archive research (Terraform Index 70,000). Before that `get_component("notebook")` returns `None`. Ship Computer research (Terraform Index 10,000) does not add it.
- Automations (scripts with no machine) need Automations research (Terraform Index 50,000).
- Library imports need Shared Library research, which comes after Ship Computer. Built-in modules (`re`, `math`, `heapq`, and others) do not need it.
- Data Archive keys: 1 to 96 characters, ASCII letters, digits, `_`, `.`, `:`, `-`. Values are JSON-safe, at most 8 nested levels and 16,384 nodes. The store holds up to 2,048 entries. `set`, `delete` and `transaction` return `ActionResult`. `get`, `has` and `keys` return natural values.
- Item flow through machine ports does nothing until Auto Feeders research is done (manual, FAQ). Scripts must move items themselves until then.

## Heat Generator (Mk I, `heater_1`, VERIFIED docs, build fe9a45c)

- VERIFIED (docs): `set_power(watts)` takes 0-10 and clamps outside that; `0` turns heating off. The setting returns to 0 when the script stops.
- VERIFIED (docs): `thermal_state()` returns `"clear"`, `"dust_storm"`, `"heat_bleed"` or `"dust_veil"`, and it changes only on a new day.
- VERIFIED (docs): `efficiency()` reads 100% only at the state's optimum, about 31% one step away, and 10% further out. The optimum values are not in the manual.
- UNVERIFIED: the step size of the peak, and whether `efficiency()` updates at once after `set_power`. `heater_1` waits one second after each probe. Checks H-001 to H-003 in `docs/in-game-test-log.md`.

## Known game-vs-Ruff difference (log evidence)

- VERIFIED (ingame log, 2026-10-17 15:46): the game reported `SyntaxError: invalid syntax at '/='` for an `oxygen_sensor.py` script at line 4. The owner's current file no longer contains `/=`, so the exact construct the game rejects is UNVERIFIED. Probe before relying on augmented assignment with `/=`.

## Probes

| Probe | Checks | Result |
|-------|--------|--------|
| `scripts/probes/probe_thermometer.py` (P-001) | version call, component lookup, thermometer read | PASS 2026-10-17 (in-game-test-log) |
| `scripts/probes/probe_control_room.py` (PX-001) | Control Room widgets, text and switch round trips, mouse, clicks, bus payload limit | Runs 3-4 PASS for the rows reported (2026-10-18); see PX-001 |

## Signal Bus (`comms`, VERIFIED docs, build fe9a45c)

- `get_component("comms")` is `None` until Signal Bus research. Queue calls (`send`, `receive`, `pending`) and broadcast calls (`broadcast`, `latest`) take channel names of 1-64 characters. Payloads are JSON-safe and at most 1,024 values. Details and statuses: `docs/game/signal-bus.md`.
- VERIFIED (docs): `pending(channel)` takes nothing; `receive(channel, id)` takes exactly that message or returns `not_found`.
- VERIFIED (docs): `latest(channel)` returns the value or `None`; it does not consume.
- VERIFIED (ingame, PX-001 run 4, 2026-10-18): `send` of a `{"req", "text"}` dict returns `ok` and `receive` returns a `CommsMessage` whose `.value` is the sent dict. A payload of 4,090 characters of text is accepted and 4,104 is rejected with `invalid_value`, so the bus limit is about 4 KB of text, below the 1,024-value rule in the docs. The exact limit is not pinned (the 4,096 boundary is a guess).
- Not yet in game: a script of ours that relies on `comms` in production. In-game checks: `docs/in-game-test-log.md`, PX-001.

## Control Room cards (VERIFIED stub for names; behaviour UNVERIFIED until D-001 to D-005)

- UNVERIFIED: a card script can import a Library (`from control_room import ...`). Libraries import in game scripts; panel scripts are not tested yet. D-001 is the first run.
- UNVERIFIED: `get_o2()` and `get_pressure()` on an unrepaired sensor. The manual says these need the sensor repaired. The cards catch any exception and show `unavailable`. The exact game behaviour (raise, or a value) is not checked; D-005 covers it.
- UNVERIFIED: builtins used by the cards (`sorted`, `enumerate`, `int`, `str`, `float`, `len`, `max`, `min`, `list +`). Assumed from the Python-like stub; `tests/test_script_imports.py` checks imports only, not builtins.
- VERIFIED stub: `panel.text_field(key, x, y, w, default, placeholder, label, size)` returns the stored text or `default`; `status_dot` takes `running`, `paused`, `error`, `idle`.
