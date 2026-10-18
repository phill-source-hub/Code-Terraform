# Spec: Rover survey and mining (rover_1)

Status: draft for owner review. Source: owner brief (Rover, Nav, Sonar, Drill, Journal, Proximity) and manual extracts in `docs/game/rover.md`. Build fe9a45c.

- **Goal**: survey the whole Nocturna map first, save it as a map with base at (0, 0), then mine the best reachable surveyed site and deliver ore home.
- **Machine**: Rover `rover_1` (self), with Nav, Sonar and Drill mounted. Module types are read from `self.modules()` at start, not assumed. Industrial/Extended research upgrades slots, so the script picks the best mounted tier.
- **Survey phase**: drive to stops on a grid sized to the mounted sonar range, scan at each stop, and survey productive contacts within range. Done when every `points_of_interest()` contact is `scanned` or listed as blocked (bounded retry, never a plain loop).
- **Target choice**: after the survey, rank surveyed mineral sites the drill can cut (hardness ≤ `drill.hardness_limit()`) by purity and distance from home. Plan the route with an energy estimate per metre; reject any site where the round trip, plus buffer, exceeds charge.
- **Unload**: home Inventory via `self.output.connect("inventory")` when parked at base. A Storage Bin within a close range of the site is used instead only if one is identified or added (not in v1).
- **Recharge**: return home when charge is below the return-trip energy plus buffer. Buffer: 20% of the trip estimate plus 5 Wh. No station or outpost is assumed unless one is set up (v1 returns to base only).
- **Safety**: every loop bounded; `brake()` before scan, survey, mine or transfer; check each `ActionResult.status`, never the message; `sleep()` for pacing; stop cancels route.

## Success criteria

- Survey covers all contacts; no contact left unclassified without a reason in the status line.
- Map (contacts, sites, base) is printed and stored when the Data Archive is available.
- Chosen target is always reachable on the current charge with the buffer.
- Rover returns to base before charge falls below the threshold; never stranded on a planned route.
- Unit tests cover grid stops, target ranking, energy gate, return threshold, blocked contacts and status-literal handling.

## Open questions (owner or in-game probe)

- Energy per metre at throttle 0.5 and 1.0 is not in the manual. v1 uses a conservative constant and logs the measured battery drop per trip to calibrate.
- Does the home base have a Vehicle Charging Station? If not, "return home to recharge" has no effect.
- Tolerance for `drill.mine()` `not_at_site` is not stated. Probe before relying on the 2 m arrival rule.
- Map size and bounds are not in the manual; the survey grid needs them (probe via `nocturna` or the map view).
- Data Archive is locked until Terraform Index 70,000 (see backlog B-001). Map is printed until then.
