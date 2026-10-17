# Drones, Fleet and Drone Service Station

Source: in-game DOCS manual, build `fe9a45c`. Sections: "Drones" (overview), "Drone", "Fleet", "Drone Service Station", types `DroneRef`, `DroneBattery`, `DroneOilTank`, `DroneCargo`. Tag: **VERIFIED (docs)**. Short notes in our own words. Safety-critical notes are marked **SAFETY**.

## Overview

- Aerial logistics and field-work units. Every drone can `go_to(x, y)` from the start; modules decide what it does on arrival.
- Electric drones: Battery Packs, slower, longer range.
- Heli drones: oil tanks, much faster.
- Cargo Pods hold one item type each.
- Unlock: Basic Drone Operations research (Terraform Index 180,000). Drone (Small) recipe unlocks with Helios, Rotor Run. Fabricate Drone (Small): 1 Rare Earth Core, 1 Titanium Ingot, 1 Control Unit, 2 t water.
- Deployment: fabricate a Drone Depot Kit and deploy it in an outpost. Keep each chassis in Inventory, select its card, use **Deploy** to commission it into a free Depot bay. Mount thruster and modules through the docked drone's service controls. Chassis and modules are service orders, not freight.
- Depot speed: Medium 2×, Large 4× base.
- Drone Service Station: charges electric drones, refuels heli drones from `oil_in`, decontaminates docked drones at 10 exposure/h, rescues stalled or scrambled drones.

## Drone (component)

Access: `self` or `get_component(id)`.

| Property | Notes |
|----------|-------|
| `.battery` | DroneBattery (electric only). `level()` Wh, `capacity()` Wh, `percent()` 0-1. Raises `ReferenceError` on heli. |
| `.oil_tank` | DroneOilTank (heli only). `level()` tons, `capacity()`, `percent()`. Raises `ReferenceError` on electric. |
| `.cargo` | DroneCargo. `count()`, `contents()`, `capacity()`, `space_for(item_id)`, `load()`, `unload()`. Loads at Depot; `load()` also at field Mining Drill or Lead Cask. Item properties preserved. Use `space_for` (life-form room is item-specific). |
| `.bio_scanner` | PortableBioScanner. `scan()` needs module, completed route, working electronics. Result via `BioScanResult.scan`. |
| `.bio_extractor` | PortableBioExtractor. `extract()` needs a hovering, non-scrambled drone. Uses a 25 t one-life-form chamber plus Cargo Pods. |

**SAFETY:** in a mixed fleet, check `DroneRef.engine` (`"electric"` or `"heli"`) before touching `.battery` or `.oil_tank`. Otherwise `ReferenceError`.

### Movement

| Method | Returns | Notes |
|--------|---------|-------|
| `go_to(x, y)` | ActionResult (self) | Any world coordinate, no module needed. Returns at once; status becomes `traveling`. Stop, end, error or `go_to_station()` cancels. Statuses: `ok`, `invalid_target`, `out_of_bounds`, `out_of_range`, `busy` (transient), `scrambled` (transient). |
| `go_to_station(name)` | ActionResult (self) | Route to a Depot or Service Station (name or id). Returns at once. Confirm arrival with `current_station()` vs stable id. Moves between same-outpost drone buildings cost no fuel. Statuses: `ok`, `station_not_found`, `out_of_range`, `busy`, `scrambled`. |
| `go_to_drill(name)` | ActionResult (self) | Fly to a deployed Mining Drill for pickup; hovers on arrival. Confirm with `current_drill()`. Statuses: `ok`, `drill_not_found`, `out_of_range`, `busy`, `scrambled`. |
| `undock()` | ActionResult (self) | Leave berth without flying. Keeps position, cargo, fuel, exposure. Throttle → 0, status `idle`. Does not end an active rescue or station charge/refuel. Statuses: `ok`, `not_docked`, `busy`. |
| `position()` | Position | `.x`, `.y` in metres. Lerped during transit, snapped on dock. |
| `get_distance_to(x, y)` | float m | Straight-line only. Ignores fuel. |
| `range_remaining()` | float m | Estimate at current energy and throttle. 0 if throttle 0 or energy empty. |
| `throttle()` | float 0-1 | Reads 0 after Stop, completion or error. |
| `set_throttle(rate)` | ActionResult (self) | 0-1. Full throttle: electric 300 m/h at 5 Wh/h; heli 900 m/h at 5 t/h oil. Burn scales with throttle squared. Status: `ok`. |

### State

| Method | Returns | Notes |
|--------|---------|-------|
| `status()` | str | Operational activity, not arrival. Values: `idle`, `traveling`, `charging`, `refueling`, `waiting_service`, `waiting_oil`, `waiting_bay`, `being_rescued`, `holding_weather`, `scrambled`, `stalled_no_battery`, `stalled_no_oil`, `stalled_no_route`. |
| `current_station()` | str | Station id where physically docked; `""` in transit or waiting outside a full Depot. Use equality with the destination id. |
| `current_drill()` | str | Drill id where cargo can load now (inside loading area, no active route). |
| `exposure()` | float 0-`exposure_capacity()` | Changes only on Raw Uranium collection and Service Station care. |
| `exposure_capacity()` | float | 100. Reaching it scrambles the drone; needs Service Station rescue. |
| `is_plated()` | bool | Shield Plating mounted: zero Raw Uranium exposure, halves Cargo Pod capacity, fuel burn ×1.5. |
| `is_being_rescued()` | bool | True while a recovery vehicle is outbound, servicing or carrying it. Pause route scripts. |
| `rescue_status()` | str | `none`, `outbound`, `charging`, `carrying`, `returning`. |

### Weather aftermath and cargo

- `collect()` (self): one batch at the drone's exact coordinate. Max **5** Storm Glass or Raw Uranium. Statuses: `ok` (`.item_id`, `.collected`), `moving`, `busy`, `nothing_here`, `no_cargo_space`, `scrambled`.
- **SAFETY (radioactive):** Raw Uranium adds **40** exposure per batch without Shield Plating, **0** with it. The batch is kept even if it scrambles the drone. Unplated: two 5-unit batches are safe; the third scrambles it.
- `nothing_here` gives no direction clue. Wrong, nearby, expired and exhausted targets all return it.

### Modules (self only for changes)

| Method | Returns | Notes |
|--------|---------|-------|
| `modules()` | list[MountSlot] | Works on any drone. `.index`, `.type` (`thruster` slot 0, `drone_module` otherwise), `.module_id` or None. |
| `couple(slot_index, module_id)` | ActionResult | Service order from Inventory. Must be docked at an operational Depot. Statuses include `ok`, `not_at_station`, `item_not_in_inventory`, `unknown_module`, `slot_not_compatible`, `slot_occupied`, `invalid_slot`, `locked`, `wrong_engine_for_module`, `cargo_capacity_exceeded`. |
| `uncouple(slot_index)` | ActionResult | Returns module to Inventory. Docked at Depot. Cargo Pods must be empty. Shield Plating cannot come off while Raw Uranium or Fuel Rods are aboard. Statuses include `ok`, `module_not_mounted`, `not_at_station`, `container_not_empty`, `hot_cargo_requires_plating`, `inventory_full`. |

## Fleet (component)

Access: `get_component("fleet")`. Read-only snapshots. Control still goes through each unit's own script or station API.

| Method | Returns | Fields |
|--------|---------|--------|
| `vehicles()` | list[VehicleRef] | `id`, `name`, `kind`, `x`, `y`, `battery_level`, `is_docked`, `current_station`, `is_being_rescued`, `rescue_status`. |
| `drones()` | list[DroneRef] | `id`, `name`, `kind` (`drone_small` / `drone_medium` / `drone_large`), `engine` (`""`, `electric`, `heli`), `current_station`, `battery_level` or `oil_level`, `is_docked`, `is_being_rescued`, `rescue_status`, `status`, `x`, `y`. |
| `mobile_units()` | list[MobileUnitRef] | Both; branch on `.category` (`"vehicle"` or `"drone"`). |

Example (docs):

```python
fleet = get_component("fleet")
for drone in fleet.drones():
    print(drone.id, drone.name, drone.status, drone.battery_level, drone.oil_level)
```

Use stable ids for station and recovery APIs.

## Drone Service Station (component)

Access: `get_component(id)`.

| Member | Returns | Notes |
|--------|---------|-------|
| `.outpost`, `.oil_in` | OutpostRef, FluidPort | `oil_in` feeds heli refuel. |
| `get_docked()` | list[str] | Drone ids docked here. |
| `charge(drone_id, target_level=1.0)` | ActionResult (self) | Electric drones. Statuses: `charging` (active), `queued`, `target_reached`, `not_docked`, `station_offline` (transient), `invalid`. |
| `refuel(drone_id, target_level=1.0)` | ActionResult (self) | Heli drones. Statuses: `refueling`, `queued`, `target_reached`, `not_docked`, `station_offline` (transient), `no_oil`, `invalid`. |
| `dispatch_rescue(drone_name, target_level=1.0)` | ActionResult (self) | Statuses: `ok`, `already_dispatched`, `station_offline` (transient), `not_found`, `not_stranded`, `invalid`. |
| `cancel_rescue()` | ActionResult (self) | Statuses: `ok`, `no_rescue`. |
| `is_rescuing()` | bool | |
| `get_rescue_target()` | str | |
| `stop(drone_id)` | ActionResult (self) | Statuses: `ok`, `not_found`, `invalid`. |
| `clear_queue()` | CountResult (self) | `.count`. Statuses: `ok`, `no_op`. |
| `get_active()` / `get_queue()` | list[str] | |
| `status(drone_id)` | dict | Per-drone status snapshot. |
| `get_bay_count()` | int | |
| `get_charge_rate(drone_id)` / `get_refuel_rate(drone_id)` | float | |

## Open questions

- Depot API (`load`/`unload` on Depot, `Drone Depot` section in the manual).
- `dispatch_rescue` on Drone Service Station versus Vehicle Charging Station (`dispatch_rescue` for vehicles): two APIs, same name. Check each entry in game.
- Numeric status for heli `"stalled_no_oil"` thresholds: not stated.
