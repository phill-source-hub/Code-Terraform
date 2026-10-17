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
- How to run: copy the file into the game's scripts folder as a machine script (name it for a machine with a script slot, see the open question in README), then Run Script in Game. Do not overwrite an existing script you want to keep.
- Expected console output (4 lines; the last line is a number in Celsius, any value is fine):
  1. `game version: <build string>`
  2. `thermometer found: True`
  3. `type_id: thermometer`
  4. `surface temp (C): <float>`
- Expected behaviour: no machine state changes; script ends.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      |              |        |       |

## Scripts

No game scripts yet. The first checklist comes with the first example script.
