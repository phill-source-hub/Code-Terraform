# Code: Terraform API notes

Short notes in our own words. Every fact has a tag:

- **VERIFIED (stub)**: seen in the game-generated `__builtins__.pyi` stub (signature and/or its docstring). Stub text is the game's own declaration, so it counts as VERIFIED for *shape*, not necessarily for in-game behaviour.
- **VERIFIED (ingame)**: a script ran in game and the result was checked against the in-game-test-log.
- **UNVERIFIED**: anything else. Do not write code that depends on it without a probe.

The stub is generated per game build and lives in the game's scripts folder, not in this repo. Re-check signatures after a game update (`get_game_version()` returns the build).

## Language

- The language is Python-like, not CPython. Builtins are a curated list in the stub (`print`, `len`, `range`, `sorted`, `isinstance`, math helpers, `itertools`/`json`/`re` style modules, `dataclasses`, `enum`, `functools`, `heapq`, `random`).
- VERIFIED (stub): `rand()` and `random()` both exist; `randint(min, max)` exists. Whether `max` is inclusive is UNVERIFIED.
- VERIFIED (stub): `def` / `class` / `isinstance` / `dataclass` are declared. `type X = ...` alias syntax appears in the game's `user_stubs.py` header, so the parser accepts it.
- UNVERIFIED: whether `exec`, `eval`, `open`, `input`, `__import__` exist. Assume no.
- UNVERIFIED: which Ruff-accepted syntax the game rejects. Record here when found.

## Output and status

- VERIFIED (stub): `print(*values, sep=, end=)` is the telemetry channel; `warn` and `debug` also exist.
- VERIFIED (stub): `set_status(message, level=)` shows a per-run status. Machine objects have `self.set_status` and `clear_status` too.
- VERIFIED (stub): `notify(text, level, duration_seconds, dismissible)` is a toast plus a Computer notification archive. Use sparingly. `level` is `info`, `warn` or `error`. Duration is clamped to 0.5 to 30 s; `0` makes it sticky. Identical notifications within 1 s collapse.
- VERIFIED (stub): `sleep(seconds)` exists. Scheduling and yield behaviour UNVERIFIED.

## Machines and components

- VERIFIED (stub): `get_component(name)` returns a typed component or `None`. Machine ids are the names in the save (for example `scanner_1`, `thermometer`, `oxygen_sensor`).
- VERIFIED (stub): every component has `id` and `type_id`.
- VERIFIED (stub): `Thermometer.get_value()` returns the surface temperature in Celsius as a float. Safe to call from any script. The stub points to `get_component("atmosphere").get_heat()` for the research heat metric, a different number.
- VERIFIED (stub): `ActionResult[...]` return types carry a status literal. Always branch on the status, never assume `ok`.
- VERIFIED (stub): `set_powered(machine_id, on)` returns a status literal including `not_enough_power` and `not_connected`.

## Power and boot

- VERIFIED (stub): `boot()` returns `booting` or `already_booted`.
- VERIFIED (stub): `activate_power()` returns `activating`, `already_online` or `boot_required`.
- VERIFIED (stub): `activate_sensors()` returns `initializing`, `already_online` or `power_required`.
- VERIFIED (ingame): the game log prints `use: activate_power()` at boot. Not yet run by us.

## Rovers, drones, fabricators, contracts, libraries

- VERIFIED (stub): `Rover` and `Fleet` types exist. `set_target`, `set_throttle`, `get_position`, `get_speed`, `get_distance_to` exist on a mobile unit with status-literal returns. Behaviour UNVERIFIED.
- VERIFIED (stub): drone classes and drone station classes exist (`DroneSmall`, `DroneMedium`, `DroneLarge`, `DroneStation*`, `DroneServiceStation`). Battery and oil types exist (`DroneBattery`, `DroneOilTank`). Behaviour UNVERIFIED.
- VERIFIED (stub): `Fabricator` and `ItemCatalog` exist. Recipes and item ids are `Literal` types. Behaviour UNVERIFIED.
- VERIFIED (stub): `ContractScript` and `Contract` types exist, with per-contract subclasses. Behaviour UNVERIFIED.
- VERIFIED (stub): `user_stubs.py` is for type aliases only. Executable helpers belong in an in-game Library (`lib/`).

## Pending: needs your pasted in-game docs

These systems have stub signatures only. Behaviour, units and limits are UNVERIFIED until you paste the in-game docs pages: rovers, power, fabricators, drones, contracts, libraries.
