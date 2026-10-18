# Spec: Rover survey and mining (rover_1) and charging station (charging_station_1)

Status: in progress on `feat/rover-survey-mine`. Source: owner brief (Rover, Nav, Sonar, Drill, Journal, Proximity, Charging Station) and manual extracts in `docs/game/rover.md`. Build fe9a45c.

- **Goal**: survey the whole Nocturna map first, save it with base at (0, 0), then mine the best reachable surveyed site and deliver ore home.
- **Machine**: Rover `rover_1` (self), with Nav, Sonar and Drill mounted. Charging Station at base runs `charging_station_1`.
- **Survey phase**: drive a grid of stops spaced at 1.2 × sonar range, scan at each stop and survey productive contacts. Then visit each unresolved contact once; a contact still unscanned after its visit is blocked and not revisited. Survey runs once, unless the Data Archive already holds `rover.map`.
- **Map**: `rover.map` in the Data Archive (unlocked): base, bounds from `nocturna.get_bounds()`, every contact, every classified site. Also printed.
- **Drill swap**: at base, `self.modules()` finds the drill slot. The highest drill tier in Base Inventory (`drill_module` < `drill_module_industrial` < `drill_module_heavy`) is mounted. The old drill is unmounted first. Slot compatibility is left to the game: a `slot_not_compatible` result keeps the current drill. Research upgrades slot types (owner correction).
- **Target choice**: surveyed mineral sites the mounted drill can cut (hardness ≤ tier limit). Rank by units times purity, then shorter trip. Units are capped by free cargo and by spare charge.
- **Energy**: not in the manual. Start at 0.05 Wh/m and calibrate from each leg (battery drop over metres driven). Legs under 10 m do not calibrate.
- **Recharge**: a visit that would leave less charge than the trip, the way home, and one scan's headroom goes home first and waits. Home is the Charging Station. Wait ends at 90%, or after a tick limit with a warning.
- **Unload**: home Inventory via `self.output.connect("inventory")` and `send` per stack, parked at base only. A close Storage Bin is not used in v1.
- **Charging station**: `charging_station_1` queues each docked vehicle to 100%. A vehicle already charging or queued is not queued again. A rover cannot charge itself (charge() is self-only on the station).
- **Safety**: every loop and wait is bounded; drives stop on arrival, stall, low charge (10%) or tick limit; `brake()` before scan, survey, mine and transfer; every result's `.status` is checked; `sleep()` for pacing.

## Success criteria

- Survey covers all contacts; unresolved contacts are listed as blocked in the status line.
- Map saved to `rover.map` and printed, base at (0, 0).
- Drill swap to the highest owned tier happens only at base, and a failed swap leaves the rover mining with the old drill.
- Chosen target is always reachable on the current charge with the buffer.
- Rover returns to base before charge falls below the return reserve, and waits there for the station.
- Unit tests: `rover_plan` (tiers, stops, energy, target choice, blocked contacts, map shape); adapter tests for the drill swap, keep-current-drill and station queueing.

## Open questions (in-game probes)

- Real Wh per metre at throttle 0.5. The runtime calibration logs the measured value; compare with the constant.
- `drill.mine()` `not_at_site` tolerance: the adapter drives to within 2 m, which may not be enough.
- Sonar swap is not automated in v1 (only the drill is swapped).
- Whether `output.send` takes ore straight from `self.cargo` at home, or needs a stack-by-stack path; check the first unload's status.
- Map is saved only if `rover.map` is absent, so a changed map is not re-surveyed automatically.
