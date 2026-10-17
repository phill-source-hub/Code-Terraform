# Rover

Source: in-game DOCS manual, build `fe9a45c`, section "Rover" (and Command Results). Tag: **VERIFIED (docs)** unless marked otherwise. Notes are short and in our own words.

## Basics

- Mining vehicle. Bare chassis does nothing; abilities come from modules in three fixed function slots.
- Energy 100 Wh. Stockpile 10 units (mixed).
- Unlock: Rover Chassis research (Pressure 0.11). Buy from Shop, 2,000 cr.
- Access: `self` in its own script, or `get_component(id)`. IDs are case-sensitive; the ⓘ on the machine card shows the exact id.

## Properties

| Property | Type | Notes |
|----------|------|-------|
| `.id` | str | Stable id. Prefer over `.name` for scripts. |
| `.name` | str | Display name. |
| `.battery` | Battery | `level()` 0-1; `wh()` raw; `capacity()` 100. Below 0.1 = near stranding. `holders()` is `[]`. |
| `.cargo` | Cargo | `count()`, `capacity()` = 10, `full()`. `discard(0)` jettisons whole hold, 1 h if cargo present. |
| `.nav` | NavModule | Needs mounted Nav Module. `set_target(x, y)`, `set_throttle(f)`, `brake()`. Both setters return immediately. Stopping, ending or failing the script stops the Rover and clears route. Distance tolerance = "close enough", not stopped: call `brake()` before mining, scanning, surveying or transfers. |
| `.sonar` | SonarModule | Needs Sonar Module. `scan()` finds sites (pauses script); `survey(site)` reveals details. |
| `.drill` | DrillModule | Needs Drill Module. `mine()` extracts one unit from surveyed site under the Rover. Vehicle must be stationary with cargo space and power. |
| `.input` | VehicleInputSlot | Load from Inventory (home), outpost storage, field stockpile, or stopped nearby vehicle. Needs Auto Feeders. Field/vehicle loads need service range; vehicle-to-vehicle needs both stopped. |
| `.output` | OutputSlot | Unload to Inventory (only when parked at home), Storage Bin, Warehouse, or stopped nearby vehicle (~2 m). Needs Auto Feeders. |

## Methods

| Method | Returns | Notes |
|--------|---------|-------|
| `status()` | str | `idle`, `moving`, `stranded`, `scanning`, `surveying`, `drilling`, `discarding`, `constructing`, `transferring`, `charging`, `queued`, `being_rescued`. Idle may still have a job or script. |
| `is_being_rescued()` | bool | True while rescue drone charges it in place. Pause movement/mining then. |
| `rescue_status()` | str | `none`, `outbound`, `charging`, `returning`. |
| `dock(station)` | ActionResult | self only. Choose a Vehicle Charging Station id/name whose service area contains the parked Rover. Statuses: `ok`, `station_not_found`, `under_construction`, `not_at_station`. Without a choice, nearest eligible station; ties broken alphabetically by id. |
| `current_station()` | str | Station id or `""`. |
| `modules()` | list[MountSlot] | One per chassis slot. `.index`, `.type`, `.module_id` (None if empty), `.internal_items`. |
| `mount(slot_index, item_id)` | ActionResult | self only. Hardware service order from Inventory. Rover must be parked in home or operational-outpost service area. Statuses: `ok`, `not_at_service_point`, `locked`, `item_not_in_inventory`, `unknown_module`, `slot_not_compatible`, `slot_occupied`, `invalid_slot`, `capability_already_mounted`. |
| `unmount(slot_index)` | ActionResult | self only. Returns module to Inventory. Container modules must be empty. Statuses: `ok`, `not_at_service_point`, `slot_empty`, `invalid_slot`, `holder_not_empty`, `inventory_full`. |
| `install(slot, internal, item_id)` | ActionResult | Not used on Rover (fixed slots take only Nav, Sonar, Drill). |
| `uninstall(slot, internal)` | ActionResult | Same as install: not for Rover. |
| `set_status(msg, level)` | None | self only. ≤240 chars, no nulls. Level `info`/`warn`/`error`. |
| `clear_status()` | None | self only. |
| `get_status_report()` | ScriptStatusReport or None | Snapshot: `message`, `level`, `active`, `run_id`. |
| `peek_command()` / `next_command()` / `command_count()` / `clear_commands()` | — | self only. Read commands sent from editor's Commands tab. See Script Commands. |

## Parking rule

"Parked" = not moving and no active throttle. A vehicle with no drive energy counts as parked whatever its throttle says.

## Known gaps in this section

- Movement units (grid vs metres) and throttle semantics beyond the two sentences above: not stated here. Check the Nav Module entry.
- `set_throttle` range: docs say 0.5 as example only.
