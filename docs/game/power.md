# Power, batteries and charging

Source: in-game DOCS manual, build `fe9a45c`. Sections: "Power & Terraforming Machines", "Power Networks", "Power Control", "Battery", "Solar Generator", "Battery Charger", "Batteries & Charging", types `PowerGrid`, `PowerGridMember`, `PowerSummary`. Tag: **VERIFIED (docs)**. Short notes, own words.

## Concepts

- **Power grid** = completed power lines touching each other. Each grid pools generation, storage and demand. Lines have no direction, loss or per-line limit.
- Touching line pieces connect. Power Bridges pass over lines without joining them.
- Outposts expose a power footprint; completed power pieces touching it join the outpost's grid. Machines with a missing or stale outpost get no power.
- Blueprint ghosts and partly built pieces carry no power.
- **Allocation**: generation serves the full live demand first. Conventional batteries cover the shortfall. Lightning Rod reserve is spent last. Lightning Rods never charge from ordinary surplus.
- **No priority, no partial shedding**: if supply cannot cover the full live load for a tick, every live consumer on that grid pauses before work runs. Canceled work spends no partial storage.
- **Recovery**: paused machines resume together once live generation covers the full returning load, or batteries plus Lightning reserve hold one hour of the deficit. Manually switched-off machines do not auto-resume.
- A split route makes separate grids immediately.
- Diagnose a dark outpost: check every wire piece and bridge is complete, ground wires touch both footprints, and generation or stored energy covers the live load.

## `power_control` (access: `get_component("power_control")`)

Snapshots are taken from the last completed allocation. Re-query on the next loop iteration after rewiring or breaker changes.

| Method | Returns | Notes |
|--------|---------|-------|
| `grids()` | list[PowerGrid] | Every independent grid, including isolated outposts and field structures. |
| `grid(target_id)` | PowerGrid or None | Grid containing an outpost, building or field structure id. None = unknown, mobile, under construction, not a power structure, or not in a completed grid. |
| `total()` | PowerSummary | Planet-wide snapshot. Battery and Lightning reserve kept separate. |
| `is_powered(machine_id)` | bool | Unknown id returns False. Safe to call first. |
| `can_power_off(machine_id)` | bool | True if the machine has a visible breaker. Batteries, passive tanks, mobile units and ship gear usually cannot. |
| `set_powered(machine_id, on)` | ActionResult | Same as clicking the card toggle. Switching off pauses that machine's scripts and keeps setpoints. Switching on resumes only scripts paused by the power-off. Statuses: `ok`, `not_found`, `not_toggleable`, `under_construction`, `not_connected`, `not_enough_power`. |

### PowerGrid fields

`anchor_id` (re-discover after rewiring), `outpost_ids` (sorted; empty for field-only grid), `machine_ids` (sorted; excludes mobile units and ship gear), `members` (list of PowerGridMember), `generated` W, `consumed` W, `net` W (negative = running on storage), `stored` Wh (conventional batteries), `capacity` Wh, `reserve_stored` Wh (Lightning), `reserve_capacity` Wh, `has_generator` bool (True even at 0 W output).

### PowerGridMember fields

`id`, `name`, `type_id` (e.g. `"solar_generator"`, `"battery"`, `"smelter"`), `outpost_id` (empty for field structures), `powered` bool, `roles` list of `"generator"`, `"consumer"`, `"storage"`, `"reserve"` (empty = connected but no electrical role), `generated` W, `consumed` W, `stored` Wh, `capacity` Wh, `reserve_stored` Wh, `reserve_capacity` Wh.

### PowerSummary fields

`grid_count`, `generated` W, `consumed` W, `net` W (planet-wide), plus stored and reserve totals.

### Example (docs)

```python
power = get_component("power_control")
for grid in power.grids():
    print(grid.anchor_id, grid.generated, grid.consumed, grid.net)
    for member in grid.members:
        print("  ", member.id, member.roles, member.generated, member.consumed)
```

## Battery (base-station storage component)

- Energy 500 Wh. Buy from Shop, 300 cr.
- Fills on surplus, drains on shortfall. If empty, machines switch off and their scripts pause.
- `get_level()` → float, current Wh. Near 0 = brownout imminent.
- `get_capacity()` → float, total Wh.
- `.outpost` → OutpostRef.
- Access: `get_component(id)`.

## Solar Generator

- Up to +50 W when tracked. Night = 0 W. Buy from Shop, 500 cr.
- `self.set_tilt(degrees)` → ActionResult (self only). Range 0° flat to 90° vertical; out-of-range values are clamped. Status: `ok`. Resets to rest tilt 90° when its script stops, ends or errors.
- `tilt()` → float, last setpoint (0-90).
- `get_output()` → float W, live. 0 when off. Compare to rated max to check the tracker holds peak.
- Standard `set_status`, `clear_status`, `get_status_report`, command methods (self only where noted).

## Battery Charger

- Charges loose Portable Batteries (50 Wh) and Heavy Portable Batteries (100 Wh) from the local grid. Idle draw 0 W.
- Research: Battery Charger (Oxygen 25). Buy 1,500 cr. Place at base or founded outpost.
- Tiers:

| Tier | Shared slots | Bays | Total power |
|------|-------------|------|-------------|
| Mk I | 4 | 1 | 30 W |
| Mk II | 8 | 2 | 60 W |

- Slots hold waiting, charging and ready cells alike. Bays limit simultaneous charging.
- Ports: `.input` (InputSlot; only portable batteries; `eject()` recovers unqueued cells, `flush()` discards them), `.output` (OutputSlot; only unqueued cells).

| Method | Returns | Notes |
|--------|---------|-------|
| `slots()` | list[BatteryChargerSlot] | Snapshots of every socket. |
| `status(slot_index)` | BatteryChargerSlot | Raises ValueError if index out of range. |
| `charge(slot_index, target_level=1.0)` | ActionResult (self) | target in (0, 1]. Repeat call updates target. Statuses: `queued`, `target_reached`, `empty`, `under_construction`. |
| `stop(slot_index)` | ActionResult (self) | Cancels job, releases cell, keeps charge. Statuses: `ok`, `no_op`. |
| `clear_queue()` | CountResult (self) | Cancels all jobs; `.count`. Statuses: `ok`, `no_op`. |
| `get_queue()` | list[int] | Unfinished sockets, ordered, incl. active. |
| `get_active()` | list[int] | Sockets charging now. Empty during outage or battery handling. |
| `tier()` | int | 1 or 2. |
| `get_slot_count()` | int | 4 or 8. |
| `get_bay_count()` | int | 1 or 2. |
| `get_bay_rate()` | float W | Nominal per bay. |
| `get_charge_rate(slot_index)` | float W | Actual rate for that socket. 0 when inactive. |

Notes:
- A completed job releases its socket. Removing a cell does not move its job to the replacement.
- Power loss pauses jobs; a job keeps running after its script stops.

## Vehicle battery and charging (summary)

- Drain: moving (main cost; high speed is costly, lower throttle is more efficient), drilling (10-30 W while drilling), sonar (0.5-3 Wh per scan or survey), stationary = free.
- Rover: fixed 100 Wh, not upgradable. Full throttle ≈ 5 h, half throttle ≈ 20 h.
- Pioneer: no built-in battery; mount battery modules.
- Vehicle battery methods: `level()` 0-1, `wh()`, `capacity()`. Below 0.1 = near stranding.
- Dead battery pauses the route; the script keeps running. The vehicle stops and clears its route on Stop, script end or uncaught error.
- Charging: park in a Vehicle Charging Station service area. `self.charge(vehicle_id, 0.8)` charges to 80%, queued per station. `dispatch_rescue(vehicle, target_level)` sends a slow field drone to a stranded rover or Pioneer. `cancel_rescue()` recalls the drone; delivered charge stays.
- Battery swap: Pioneer parked and braked in charger service area calls `self.swap_batteries("battery_charger_1", None, 0.9)`. `None` = all installed; `0.9` = minimum charge of replacements. All-or-nothing: each replacement needs an unqueued cell of the same type at or above threshold, else nothing changes.

## Open questions (not in these pages)

- Exact `status` strings for `dispatch_rescue`, `cancel_rescue`, `swap_batteries`: check their own DOCS entries; not yet extracted.
- Whether `charge(slot_index, target_level)` in docs matches the stub signature exactly: confirm in game.
