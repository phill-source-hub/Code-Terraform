# Fabricator and item ports

Source: in-game DOCS manual, build `fe9a45c`. Sections: "Fabricator", "Fabricator Recipes" (first entries only), types `InputSlot`, `OutputSlot`, `Recipe`, `ItemStack`, `TransferResult`. Tag: **VERIFIED (docs)**. Short notes, own words. Full status lists are in the manual; only the common ones are copied here.

## Fabricator

- Assembles finished parts from several refined materials. Script picks a recipe, gathers each ingredient into the shared stockpile, drains output.
- Unlock: Fabrication research (Terraform Index 130,000). Buy 1,400 cr.
- Tiers: Mk II and Mk III documented. `tier()` → 1, 2 or 3.
- Stockpile: 200 units mixed. Fluid process buffers 10 t each (steam, water, oil).
- Output buffer 20 units. Byproduct buffer 20 units.
- Power: variable, draws from grid.
- 75 recipes available.
- Access: `self` or `get_component(id)`.

### Ports

| Port | Type | Use |
|------|------|-----|
| `.input` | InputSlot | Feeds the multi-material stockpile. Inventory works at home only. Needs Auto Feeders. |
| `.output` | OutputSlot | Finished items. Inventory at home only. Needs Auto Feeders. |
| `.byproduct` | OutputSlot | Secondary output (oil recipes emit tar here every craft). Bin must have room or the recipe stalls. Needs Auto Feeders. |
| `.steam_in` | FluidPort | Process buffer for recipes with `fluid_inputs["steam_in"]`. `connect(id)` to a Thermal Cap or steam Gas Tank. |
| `.water_in` | FluidPort | For `fluid_inputs["water_in"]`. `connect(id)` to Water Pump, Steam Condenser, or water tank. |
| `.oil_in` | FluidPort | For `fluid_inputs["oil_in"]`. `connect(id)` to Oil Pump or oil tank. |

Read `level()` / `flow_rate()` on fluid ports to detect starvation. Remote fluid sources need a completed, conflict-free pipe route.

### Methods

| Method | Returns | Notes |
|--------|---------|-------|
| `tier()` | int | 1, 2 or 3. |
| `list_recipes()` | list[Recipe] | Only unlocked recipes. Sort with `key=lambda r: r.tier`. |
| `find_recipe(recipe_id)` | Recipe or None | None if unknown, locked, or not this machine's. |
| `set_recipe(recipe_or_id)` | ActionResult (self) | Does not clear stockpile; leftovers stay until used or `self.input.flush()`. Statuses: `ok`, `unknown_recipe`, `offline` (transient), `recipe_locked`, `busy` (transient), `material_mismatch`. |
| `clear_recipe()` | ActionResult (self) | Idle the machine. Stockpile kept. Statuses: `ok`, `busy` (transient), `material_present`. |
| `get_recipe()` | str | Current id, or `""`. |
| `get_recipe_inputs()` | dict[str, int] | `{item_id: count per craft}`, or `{}`. |
| `get_stockpile()` | dict[str, int] | Current contents. |
| `get_stockpile_used()` | int | Total units stored. |
| `get_stockpile_capacity()` | int | Combined cap (fixed for this machine). |
| `is_running()` | bool | True while crafting. |
| `get_progress()` | float 0-1 | Resets to 0 when a craft finishes. |
| `get_output_count()` | int | Completed units waiting. Drain before buffer fills, or processing stalls. |
| `set_status`, `clear_status`, `get_status_report`, command methods | — | Standard. See Command Results. |

Blocking rule: when the stockpile is full, input is blocked until the running craft consumes material.

## Recipes

A `Recipe` has: `tier`, `id`, `name`, `inputs` (dict item→count), `output_item`, `output_count`, `duration_game_hours`, `power_draw` (W), `fluid_inputs` (dict fluid→tons per run), `input_fluid`, `fluid_outputs`, `output_fluid`, `byproduct_item`, `byproduct_count`.

Example entries from the manual (build `fe9a45c`):

| Recipe id | Inputs | Output | Craft time (Mk I / II / III) | Power (Mk I / II / III) | Unlock |
|-----------|--------|--------|------------------------------|-------------------------|--------|
| `craft_smelter_pack_mk2` | 2 Machine Frame, 2 Control Unit, 2 Pressure Valve, 2 t water | Smelter Mk II Upgrade Pack | 1 h / 0.5 h / 0.25 h | 60 / 90 / 180 W | Industrial Machinery Mk II |
| `craft_fabricator_pack_mk2` | 2 Machine Frame, 2 Control Unit, 4 Circuit Panel, 2 t water | Fabricator Mk II Upgrade Pack | 1.1 / 0.55 / 0.28 h | 65 / 97.5 / 195 W | Industrial Machinery Mk II |
| `craft_oil_pump_pack_mk2` | 2 Machine Frame, 1 Control Unit, 3 Pressure Valve, 2 Cobalt Ingot, 2 t water | Oil Pump Mk II Upgrade Pack | 1 / 0.5 / 0.25 h | 60 / 90 / 180 W | Advanced Oil Extraction |

Other recipe ids seen in the `get_recipe()` list: `craft_fabricator_pack_mk3`, `craft_smelter_pack_mk3`, `craft_gas_pipe_segment`, `craft_liquid_pipe_segment`, `craft_power_line_segment`, `craft_gas_pipe_bridge`, `craft_liquid_pipe_bridge`, `craft_power_line_bridge`, `craft_pressure_valve`, `craft_machine_frame`, `craft_circuit_panel`, `craft_control_unit`, `craft_battery_cell`, `craft_thermal_cap_kit`. Most blueprints come as contractor order rewards. Full table: manual "Fabricator Recipes".

Example from manual: `self.set_recipe("craft_gas_pipe_segment")`.

## Port API (`InputSlot`, `OutputSlot`)

Both share one shape. Port belongs to a stationary machine with a buffer.

| Method | Returns | Notes |
|--------|---------|-------|
| `connect(name)` | ActionResult | Source (InputSlot) or destination (OutputSlot) by stable id or display name, or `"inventory"`. Same outpost required for stationary endpoints. Rover/Pioneer reachable from any outpost only while parked in this machine's service area. Drone cargo moves via its Drone Depot. Statuses: `ok`, `not_found`, `not_local`, `same_endpoint`, `unsupported_source`/`unsupported_target`, `source_is_vehicle`/`target_is_vehicle`. |
| `disconnect()` | ActionResult | Statuses include `ok`. |
| `connected_to()` | str | Display name of connection, or `""`. |
| `connected_id()` | str | Stable id of connection, or `""`. Prefer for comparisons. |
| `take(item_id, count, properties=None, property_match=None)` | TransferResult | InputSlot only: pull from connected source. Requires Auto Feeders. |
| `send(item_id, count, properties=None, property_match=None)` | TransferResult | OutputSlot only: push to connected destination. |
| `eject(destination, item_id, count, ...)` | TransferResult | InputSlot only: recover unqueued items from buffer to a local destination or `"inventory"` at Nocturna Base. |
| `flush()` | TransferResult | Permanently discard buffered items. On processing machines also cancels the craft in progress. |
| `count()` | int | Units buffered. |
| `capacity()` | int | Buffer max. |
| `stacks()` | list[ItemStack] | Snapshot; same id may appear twice if properties differ. |

Property matching (`property_match`): `"any"` ignores properties; `"subset"` (default when a dict is given) matches stacks containing those properties; `"exact"` requires full identity. `None` with `"exact"` selects propertyless items only.

### TransferResult

- Fields: `.status`, `.message`, `.requested`, `.moved`.
- Common statuses:
  - `ok`: moved all requested (`.moved`).
  - `partial`: moved some (`.moved` of `.requested`).
  - `no_op`: nothing requested, no change.
  - `busy` (transient): endpoint busy with another material operation.
  - `research_required`: transfer research not unlocked.
  - `no_connection`: no source/destination configured.
  - `source_empty`, `source_wrong_material`, `source_reserved`, `source_changed` (transient).
  - `buffer_full`, `slots_full`, `target_full`, `target_wrong_material`.
  - `hot_cargo_requires_cask`: radioactive items need a Lead Cask.
  - `wrong_biome`: biological material incompatible with destination.
  - `out_of_range`, `source_moving` / `target_moving` (vehicle handoffs need stops).
- Full lists: manual, each port's Outcomes table.

## ItemStack

- Import: `from __builtins__ import ItemStack` (manual example). Stub: `ItemStack` class exists.
- `ItemStack(id, count, properties=None)`. Creating one changes nothing in the world.
- `TypeError` on wrong args, `ValueError` on out-of-range numbers, `OverflowError` on unsafe integers.
- Properties: `.id`, `.count`, `.properties` (dict or None). Different properties = separate stacks, never merge.

## Open questions

- `TransferResult` payload fields on `take()` when `"partial"`: confirm in game.
- Whether `inputs` for Recipe is always a dict in game (manual says dict).
