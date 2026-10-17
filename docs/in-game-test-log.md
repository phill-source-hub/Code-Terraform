# In-game test log

L3 acceptance. Each script gets a checklist. The owner runs it in game and records the result. The orchestrator then updates the status.

A script is not Done until L1 (format and lint), L2 (pytest) and L3 (this log) pass, or the owner waives L3 in writing here.

## Template

### <script name>

- Where it runs: machine `<id>` or Library `lib/<name>`
- Setup state: (power, machines, inventory, research the script needs)
- How to run: (rerun on save, or Run Script in Game)
- Expected console output: (exact lines)
- Expected behaviour: (what the machine or world does)

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      |              |        |       |

## Probes

### P-001: version, component lookup, thermometer read

- Script: `scripts/probes/probe_thermometer.py`
- Where it runs: attach to a machine script slot or use Run Script in Game. Read-only.
- Setup state: save open, game unpaused. No power needed for the thermometer (`powered: true` in the save).
- How to run: already copied to the game as `scanner_1.py` (its empty placeholder). Open the `scanner_1` machine and press Run Script in Game. Afterwards restore `scanner_1.py` to empty or leave the probe there until the next probe.
- Expected console output (4 lines; the last line is a number in Celsius, any value is fine):
  1. `game version: <build string>`
  2. `thermometer found: True`
  3. `type_id: thermometer`
  4. `surface temp (C): <float>`
- Expected behaviour: no machine state changes; script ends.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      |              |        |       |

## Machines

### S-001: Solar tracker (`solar_1`)

- Script: `scripts/main/solar_1.py` (self-contained, ADR-014). Rule: tilt = 90 - sun elevation, from `clock.get_elevation()`. Library copy: `scripts/libs/solar_tracker.py` (tested source; not imported by the game).
- Where it runs: machine `solar_1`, a Solar Generator. Buy one from the Shop (500 cr) and name it `solar_1` if the id differs.
- Setup state: sun up. Tilt is at 90 (rest) when the script starts.
- How to run: Run Script in Game on `solar_1`. It samples every 1/12 of a world hour (about 5 world minutes).
- Expected: status bar `tilt <N> deg` (info). `N` = 90 minus the sun's elevation, so it drifts as the sun moves. At night the status shows `tilt 90.0 deg`.
- Expected behaviour: `get_output()` is near the daytime maximum once the tilt has settled. Tilt is never outside 0-90.
- Pass criteria: no error status. Output stays near its peak through the day. Stopping the script returns the panel to 90.
- Open risk: the rule assumes the manual's geometry (tilt complements elevation). If output is low at midday, note the tilt and output values here.
- Pre-req: sync `solar_tracker` Library is not needed (the script is self-contained). Shared Library research is not needed.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 (night) | fe9a45c | PARTIAL PASS | Night check: status `tilt 90.0 deg`, script `solar_1` running, no new errors in log. Midday check still pending. |

## Contracts

### C-001: Orbital Relay Hack (`relay_hack`)

- Script: `scripts/contracts/relay_hack.py`, synced to the game root as `relay_hack.py` (applied 2026-10-17). Library: `lib/relay_hack.py` (synced).
- Where it runs: the contract script for `relay_hack`. Open the contract from the Contracts page (View Contract) and confirm its script is the synced one.
- Version: self-contained (no imports, ADR-013). Earlier runs failed with `Shared Library not yet researched` on `lib/` import.
- Setup state: `relay_hack` contract available (status `available`). Transmitter has earth in `list_planets()`.
- How to run: run the contract script once.
- Expected console: one line `correct <message>` and the contract shows `completed` with its reward paid. Seeing `relay_hack failed: ...` means the search failed. Paste that text.
- Expected behaviour: at most 100 `intercept` calls (one per candidate value, all six tumblers set to that value). Stops as soon as all six are True.
- Pass criteria: transmit status `correct`. Contract status `completed`. Credits go up by the reward.
- Open risk: the manual gives no attempt limit for `intercept` (UNVERIFIED). If the lock locks out after a few wrong probes, the 100-probe sweep will fail. Note any lockout text here.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 (log 16:14 UTC) | fe9a45c | PASS | Log: `correct transmitter.transmit completed with status "correct"`. Contract script status `completed`. Two earlier runs failed on Shared Library import (fixed by ADR-013). Reward and credits not checked yet. |

### X-001: Xenogenetics Survey (`xenogenetics`)

- Script: `scripts/contracts/xenogenetics.py`, synced to the game root as `xenogenetics.py` (applied 2026-10-17, replacing the `Help me` request).
- Briefing (owner-supplied): send every one of the 1000 samples not in the 50-sequence Earth reference, as a list.
- Expected console: `<N> alien samples sent: correct <message>`. `N` is the number of samples not in the reference.
- Pass criteria: transmit status `correct`. Contract status `completed`.
- Open assumption: duplicates among alien samples are kept. If Earth rejects the answer as `incorrect`, check deduplication first and note it here.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 | fe9a45c | PASS | Owner reports correct. Log: `contract_xenogenetics: completed`. |

### X-002: Corrupted Archive (`corrupted_archive`)

- Script: `scripts/contracts/corrupted_archive.py`, synced to the game root as `corrupted_archive.py`.
- Briefing (owner-supplied): 10x10 grid, 50 words each appearing twice. Transmit `[row1, col1, row2, col2]` for each pair.
- Method: reads each cell once (100 `flip` calls), pairs on second sighting.
- Expected console: `50 pairs sent: correct <message>`.
- Pass criteria: transmit status `correct`. Contract status `completed`.
- Failure lines: `corrupted_archive failed: ...` means nothing was sent. Paste that line.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 | fe9a45c | PASS | Owner reports correct. Log: `contract_corrupted_archive: completed`. |

## Scripts

### power_monitor (machine `harvester_1`, file `harvester_1.py`)

- Where it runs: machine `harvester_1`. Self-contained (ADR-014): no library import, so no Shared Library research is needed. Version of 2026-10-17 supersedes the earlier `lib/power_status.py` import.
- Setup state: at least one powered grid. A deficit needs a consumer that draws more than generation (for example, unplug or power down a generator, or add load). Low battery needs a battery under 20 % charge.
- How to run: Run Script in Game on `harvester_1`. It keeps running and polls every 5 s of game time.
- Expected output, healthy grid: console line `power ok`, status bar info `power ok`. Printed once, not every poll.
- Expected output, deficit: console warning `power deficit: net -<N> W`, status warn with the same text.
- Expected output, low battery: console warning `low battery: <N>% stored`.
- Expected behaviour: no machine state changes. Stop script ends the loop.
- battery_1: status line also shows `| battery_1 <N>%` (status only, not printed). If battery_1 is under 20%, a warning `battery_1 low: <N>%` appears once. If battery_1 does not exist, the status has no battery part.
- Pass criteria: each state above shows once and changes only when the state changes.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      |              |        |       |
