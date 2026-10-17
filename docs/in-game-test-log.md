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
|      |              |        |       |

## Scripts

### power_monitor (machine `harvester_1`, file `harvester_1.py`)

- Where it runs: machine `harvester_1`. Library `lib/power_status.py` is also copied.
- Setup state: at least one powered grid. A deficit needs a consumer that draws more than generation (for example, unplug or power down a generator, or add load). Low battery needs a battery under 20 % charge.
- How to run: Run Script in Game on `harvester_1`. It keeps running and polls every 5 s of game time.
- Expected output, healthy grid: console line `power ok`, status bar info `power ok`. Printed once, not every poll.
- Expected output, deficit: console warning `power deficit: net -<N> W`, status warn with the same text.
- Expected output, low battery: console warning `low battery: <N>% stored`.
- Expected behaviour: no machine state changes. Stop script ends the loop.
- Pass criteria: each state above shows once and changes only when the state changes.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      |              |        |       |
