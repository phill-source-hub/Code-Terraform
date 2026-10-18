# Spec: Heat Generator (heater_1)

Status: draft for owner review. Source: owner brief and the manual (build fe9a45c), Heat Generator and Tier 3 Progression.

- **Goal**: hold the Mk I heater at the best power for today's `thermal_state()`, so efficiency reads 100%.
- **Discovery**: no optimum is given. For a state the script has not seen, it tries 0.1, 0.2 … 10.0 with `set_power`, reads `efficiency()`, and keeps the first value that reads 100% (within 0.5 points). Each state is searched once and remembered.
- **Day change**: the state is read every pass. A scan that sees the state change mid-search is discarded, because its readings belong to the old state.
- **No optimum**: if a full scan finds nothing, the script warns, sets power 0 for that state, and does not rescan it until a restart.
- **Pacing**: one pass per second; each scan probe waits one second before it reads efficiency.
- **Restart**: the table is lost on a game reload or script restart and the scan runs again. Keeping it in the Data Archive is a later step (needs Data Archive research).
- **Power**: power returns to 0 when the script stops (manual). The script never sets power above 10 (the manual clamps it there anyway).

## Success criteria

- Efficiency reads 100% for each state the script meets, within one day of each new state.
- The status line shows state, power, efficiency and output, and changes only when they change.
- Unit tests cover discovery, reuse, day change mid-scan, no-optimum, rejected calls and pacing.

## Open questions (owner)

- Step size: 0.1 is a guess. The manual does not give the peak width. If the optimum is missed at 0.1, use a finer step and log it.
- Whether `efficiency()` updates immediately after `set_power` or needs the one-second wait. Check in game (in-game-test-log, H-001).
- Mk II to Mk IV upgrades (`tier()`) are not handled. The brief covers the Mk I heater only.
