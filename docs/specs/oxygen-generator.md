# Spec: Oxygen Generator (o2gen_1)

Status: draft for owner review. Source: owner-supplied in-game text for o2gen_1 and the manual (build fe9a45c).

- **Goal**: keep the Mk I Oxygen Generator running at peak efficiency with no stalls.
- **Machine**: `o2gen_1`, Mk I (-8 W, up to 0.240 ppt/day at peak). Script runs on the generator (`self`).
- **Inputs**: CO2 level from `get_component("atmosphere").get_co2()` (ppt). Waste from `self.waste()` (0-100). Penalty from `self.dump_penalty()`.
- **Each pass**: set intake to CO2 / 10 (`self.set_intake`); if waste is 50 or more, dump (`self.dump_waste()`).
- **Success**: efficiency reads 100% when intake = CO2/10 and waste is at or below 60 with no penalty. Waste never reaches 100 (stall). Penalty stays 0 when the dump lands in 50-60.
- **Safety limits**: intake is never set outside what `set_intake` accepts (a rejected call is shown as a warning). Waste is dumped as soon as it reaches 50, so it does not drift past 60 between polls. A dump above 60 is still taken (penalty) rather than letting waste reach the stall at 100.
- **Pacing**: one pass per 1/60 world hour, the same pacing as the solar tracker. Intake returns to 0 when the script stops (manual), which is safe.

## Open questions (owner)

- Waste accumulation rate per world hour is not in the manual. The 1/60-hour pass is a guess. Check how fast waste climbs in game.
- Is the Oxygen Generator built and named `o2gen_1`? If not, the script waits (error status).
- Do we accept a penalty when waste overshoots 60, or pause production instead? The script takes the penalty.
