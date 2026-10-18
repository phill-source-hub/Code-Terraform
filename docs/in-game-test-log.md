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
| 2026-10-17 (log 17:58 UTC) | fe9a45c | PASS | Log: `game version: fe9a45c`, `thermometer found: True`, `type_id: thermometer`, `surface temp (C): -63`. Four lines as expected. |

## Machines

### S-001: Solar tracker (`solar_1`)

- Script: `scripts/main/solar_1.py` (self-contained, ADR-014). Rule: tilt = 90 - sun elevation, from `clock.get_elevation()`. Library copy: `scripts/libs/solar_tracker.py` (tested source; not imported by the game).
- Where it runs: machine `solar_1`, a Solar Generator. Buy one from the Shop (500 cr) and name it `solar_1` if the id differs.
- Setup state: sun up. Tilt is at 90 (rest) when the script starts.
- How to run: Run Script in Game on `solar_1`. It samples every 1/60 of a world hour (about 1 world minute).
- Expected: status bar `tilt <N> deg` (info). `N` = 90 minus the sun's elevation, so it drifts as the sun moves. At night the status shows `tilt 90.0 deg`.
- Expected behaviour: `get_output()` is near the daytime maximum once the tilt has settled. Tilt is never outside 0-90.
- Pass criteria: no error status. Output stays near its peak through the day. Stopping the script returns the panel to 90.
- Open risk: the rule assumes the manual's geometry (tilt complements elevation). If output is low at midday, note the tilt and output values here.
- Pre-req: sync `solar_tracker` Library is not needed (the script is self-contained). Shared Library research is not needed.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 (night) | fe9a45c | PARTIAL PASS | Night check: status `tilt 90.0 deg`, script `solar_1` running, no new errors in log. Midday check still pending. |
| 2026-10-17 (afternoon, 78° sun) | fe9a45c | PASS (tracking) | Tilt 11° vs rule 12°: within the sampling lag at 1/12-hour sampling. Output 43/50 W, efficiency 87%. |
| 2026-10-17 (morning, 90° sun, sample 1/60 h) | fe9a45c | PASS | Tilt 0°, output 50/50 W, efficiency 100%. Rule holds exactly. Efficiency falls with lower sun elevation, not only with tilt error (UNVERIFIED model). |
| 2026-10-18 (ADR-033 sync, one file on solar_1 to solar_5) | fe9a45c | PASS (owner report) | Owner reports all in-game checks completed successfully. Details not pasted into this log. |
| 2026-10-18 (ADR-033 sync, one file on solar_1 to solar_5) | fe9a45c | PENDING | Synced 2026-10-18 on owner go-ahead; `status` shows all five solar slots running, no solar errors. Check: `self` is the generator on each slot (status `tilt <N> deg` on every slot, no `set_tilt` error), and `self.id` is not read by the script. UNVERIFIED: `self.id` on a machine script. |

## Scanner and harvester

### SC-001: Scanner sweep (`scanner_1`)

- Script: `scripts/main/scanner_1.py` (replaces the P-001 probe, which passed). Self-contained.
- Setup: scanner powered; a few sectors around E13 have items.
- Prerequisite: Data Archive research (for the saved map). Without it the scan still runs but nothing is saved.
- Run: Run Script in Game on `scanner_1`.
- Expected: one snake pass over all 192 sectors (A1 to A24, then B24 to B1, and so on). Console lines for found items only. Status bar `map of 192 sectors saved` at the end. Repeats every world hour.
- Pass: 192 scans, each sector once per pass. The Data Archive key `scanner.map` holds 192 entries with status, name and value. Check it in Computer > Data Archive.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      | fe9a45c      |        |       |

### HV-001: Harvester collect and store (`harvester_1`)

- Script: `scripts/main/harvester_1.py`. Replaces the power monitor on this slot; the monitor is parked in `scripts/parked/power_monitor.py`.
- Setup: SC-001 passed (scanned items exist). Harvester at E13. Inventory has room.
- Run: Run Script in Game on `harvester_1`.
- Expected: moves one cell per pass toward the nearest item (row first, then column). On arrival: collect, then `stored <item_id> from <sector>` printed. Heat stays under 80; status `cooling` appears above that.
- Pass: the first item is collected and stored; the harvester moves between items without refusal; no `move too_far` warnings.
- Planning: each trip is chosen by path heat (item cell 1, other cell 7), then steps. A trip that would reach heat 80 waits with status `cooling before the next trip`.
- Each `stored` line now ends with `heat <N>`, the heat after the trip. Compare it with the planner's estimate (path heat from the map) to check the heat model.
- Position is read from the game each pass (`get_position`), so the start cell does not matter. Check the first move's sector in the log matches the harvester's real position.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      | fe9a45c      |        |       |

## Atmosphere

### O-001: Oxygen generator (`o2gen_1`, Mk I)

- Script: `scripts/main/o2gen_1.py` (spec: `docs/specs/oxygen-generator.md`). Applied 2026-10-17, replacing the `Help me` request.
- Setup: generator powered (-8 W); CO2 reading available; Auto Feeders not needed (no item ports).
- Run: Run Script in Game on `o2gen_1`. The loop runs continually (no sleep).
- 2026-10-18 sync (ADR-034): `o2gen_1` to `o2gen_3` now run one shared file, with rejected-call warnings printed once per change. Check: no repeating `warning: set_intake` or `warning: dump` lines in the log while a fault lasts. Pressure sync (2026-10-18, owner-approved overwrite): `pressure_1` and `pressure_2` held the pre-change text (checked by hash), so their sync state was corrected and they were written. `pressure_1` to `pressure_3` now run one shared file; `status` shows all three running.
- Expected: status `intake <CO2/10> waste <w> eff <e>% penalty <p>`, updated when it changes. Console `dumped waste at <w>, penalty 0.0` each time waste is in 50-60. Efficiency 100% with waste at or below 60.
- Warning `waste <w> is above 60; not dumping until 90` means the window was missed. Waste between 60 and 90 waits.
- At 90 or above the script takes a last-resort dump: `LAST RESORT dump at <w>, penalty <p>`. Paste it. A non-zero penalty is expected only here.
- Pass: intake tracks CO2/10 exactly. Each dump happens at 50-60 with penalty 0.0. No `above 60` warning. Waste never reaches 100. Stopping the script sets intake to 0.
- Fail signs: `warning: set_intake ...` or `warning: dump ...` in the console; a penalty above 0 after a dump in the 50-60 window (paste the status line).

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 (log 18:59 UTC) | fe9a45c | PARTIAL PASS | Log: `dumped waste at 50, penalty 0` twice (18:57, 18:59 UTC). No warnings or errors. Intake and efficiency not yet checked. |
| 2026-10-18 (ADR-034 sync, o2gen_1 to o2gen_3) | fe9a45c | PASS (owner report) | Owner reports all in-game checks completed successfully. Details not pasted into this log. |
| 2026-10-17 (panel) | fe9a45c | PASS | Intake 5000 ppt (status 4999.99) against CO2 about 50,000 ppt: CO2/10. Efficiency 100%, penalty 0, output 0.240 ppt/day (Mk I peak). Waste 34.4 and rising toward the next clean dump at 50. |

## Atmosphere (pressure)

### PG-001: Pressure generators (`pressure_1`, `pressure_2`, Mk I)

- Scripts: `scripts/main/pressure_1.py` and `pressure_2.py` (same program; test keeps them identical). Applied 2026-10-17, replacing the `Help me` requests.
- Setup: both powered (-7 W each). Script running on each.
- Run: Run Script in Game on each generator. The loop runs continually.
- Expected: status `gauge <g> window <low>-<high> efficiency <e>%`, updated when it changes. Efficiency climbs toward 100% after several sweeps. Console `warning: sync <status>` only if a sync is refused.
- Pass: efficiency rises and holds near 100%. Each sweep gets one sync inside its window. No refused syncs.
- Fail signs: efficiency stuck at 0% across sweeps, or falling. Paste the status line with the window values.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-18 (ADR-034 sync, pressure_1 to pressure_3) | fe9a45c | PASS (owner report) | Owner reports all in-game checks completed successfully. Details not pasted into this log. |

## Biology (Bio Collector, Bio Lab, Bio Exchange)

Prerequisites before any run: each machine powered; Auto Feeders researched (scripted transfers); reagents bought from the Shop Biology category and in home Inventory; Lab and Exchange at Nocturna Base.

### B-001: Bio Collector (`bio_collector_1`)

- Script: `scripts/main/bio_collector_1.py` (rewritten 2026-10-18: multi-item orders, stock and in-flight counted, idle when nothing is needed).
- Setup: collector powered; Bio Lab at the same outpost; an open Bio Order for this outpost's biome with two or more fragments, at least one not yet in stock.
- Run: Run Script in Game on `bio_collector_1`.
- Expected: status `collected a specimen <distance> m away` (info) per specimen, then `holding a specimen for the Bio Lab` while cargo is full.
- Pass: with an order needing fragments A and B (A already in Inventory), the collector moves on to B and does not collect A again. Once every needed unit is in flight or in stock, it explores unknown locations or goes idle with `no fragment to collect for the open Bio Orders`.
- Fail signs: `collect cargo_occupied` or `collect busy` repeating (paste the status); the same fragment collected more times than the order requires.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-18 | fe9a45c | PASS (owner) | Collects only for the Bio Order the Exchange is working on (status `order: ms_chelicera`); counts stock in Inventory and in-flight units; explores only while a biome type is missing from the Journal. Found and fixed during test: status overflow stopped the script (240-char limit), and collecting for all open orders. |

### B-002: Bio Lab (`bio_lab_1`)

- Script: `scripts/main/bio_lab_1.py` (rewritten 2026-10-18: buys missing reagents, ejects stray input, unloads wrong reagents, ships output first).
- Setup: B-001 passed (specimen in collector cargo). Shop has the recipe's reagents at the prices in `docs/game/manual/242-lab-reagents.md`. Auto Feeders researched. Lab at Nocturna Base.
- Run: Run Script in Game on `bio_lab_1`.
- Expected status sequence per specimen: `specimen taken from the collector`, `analyzed <name>`, `bought <reagent>` (only if Inventory was short), `staging <reagent>`, `loaded <reagent>`, `sample staged for shipping`, `sample shipped` is NOT printed (ship is silent); the sample then appears in Inventory.
- Pass: one sample per specimen reaches Inventory; the chamber is empty again; the output is empty; the input holds no reagent.
- Test 2 (restart): stop the script after `loaded <reagent>`, then run it again. It must resume the same specimen, not buy the reagent twice, and not extract a second sample.
- Test 3 (no credits): set credits below the shortfall. Expect `warning: buy <reagent>: insufficient_credits`, the specimen kept, and no `extract`.
- 2026-10-17 (owner report): samples stuck in the output port. Scripted `send` needs Auto Feeders, so the port could not drain and extraction kept going. Fixed: the lab ships the output first, extracts only when the output is empty, and discards the specimen only after a successful ship. Until Auto Feeders is researched, a refused send is shown as `output not shipped: research_required`, and the specimen is kept.
- 2026-10-17 (Auto Feeders unlocked): intermittent failures. Log showed no take or reagent messages, because those were status-only. Now every blocked step is printed as `warning: ...`. Load uses the amount the take moved. Any other reagent in the input is ejected before a take, since the port holds one reagent type at a time. `discard` returning `input_empty` is expected and not a warning.
- Assumption to check: one sample per specimen. If the lab extracts again from the same specimen before discarding, or the discard fails, note it here. A discard that reports `output_full` leaves the specimen in place, and the next pass may extract again.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-18 | fe9a45c | PASS (owner) | Exchange no_input loop fixed (sample returned with warning). Owner reports the Chelicera order flow works end to end, and the Lab's restart and no-credits tests pass. |

### B-003: Bio Exchange (`bio_exchange_1`)

- Script: `scripts/main/bio_exchange_1.py` (rewritten 2026-10-18: multi-item orders, staged samples always delivered, surplus returned to Inventory, unfillable orders passed over).
- Setup: B-002 has produced samples in Inventory. Nocturna Base only. At least one Bio Order not complete.
- Run: Run Script in Game on `bio_exchange_1`.
- Expected: `staging <id> for <order>`, then `delivered toward <order>`, and `order complete: <order>` when filled. `waiting for samples for <order>` when stock is short.
- Pass: an order with two fragments is filled with one of each, and the reward is paid. An order that needs a variant (glow or genes) that Inventory cannot supply is not assigned.
- Restart test: stop the script while a sample is staged in its input, then run it again. It must deliver that sample, not get stuck.
- Fail signs: `take <status>` or `deliver <status>` (warn), paste the status.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-18 | fe9a45c | PASS (owner) | Owner reports the Exchange order flow works end to end, including multi-fragment orders and restart. |

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

### X-004: Alien Terminal Breach (`terminal_breach`)

- Script: `scripts/contracts/terminal_breach.py`, synced to the game root as `terminal_breach.py`.
- Briefing (owner-supplied): 15 digits, each 1-5. `guess` returns `.correct` and `.misplaced`.
- Method: reads only `.correct`. Guess all-`base` once, then change one position at a time. Up to 61 guesses plus one check guess.
- Expected console: `correct <message>`.
- Pass criteria: transmit status `correct`. Contract status `completed`.
- Failure lines: `terminal_breach failed: ...` means nothing was sent. Paste that line.
- Check in game: `terminal.length` is a property; `.correct` follows the briefing rule with repeated digits (see `docs/game/contracts-terminal-breach.md`).

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 | fe9a45c | PASS | Owner reports contract complete. Log: `script contract_terminal_breach: completed`. |

### X-003: Underground Data Tablet (`data_tablet`)

- Script: `scripts/contracts/data_tablet.py`, synced to the game root as `data_tablet.py`.
- Briefing (owner-supplied): 30x30 tablet, probe distance 0 marks message cells. Transmit the distance-0 characters, row-major.
- Method: probes all 900 cells once, row-major, and builds the message in one pass.
- Expected console: `<N> chars sent: correct <message>`.
- Pass criteria: transmit status `correct`. Contract status `completed`.
- Failure lines: `data_tablet failed: ...` means nothing was sent. Paste that line.
- Check in game: `rows` and `cols` are properties; probe on a message cell returns its own char (see `docs/game/contracts-data-tablet.md`).

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 | fe9a45c | PASS | Owner reports contract complete. Log: `script contract_data_tablet: completed`. |

## Scripts

### power_monitor (SUPERSEDED by the base_watch Automation, ADR-029; was machine `harvester_1`)

- Status: removed from the repo on `feat/base-watch-automation` (ADR-029). The check below is the last run of the old monitor; base_watch has its own checklist (section "base_watch").

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
| 2026-10-17 (log 17:58 UTC) | fe9a45c | PARTIAL PASS | Log: `power ok` printed once, script running. Deficit and low-battery warnings not yet seen. Status bar text not checked. |

## Library imports (ADR-025, branch refactor/shared-libs)

- Check: each script that imports a Library runs in game. Scripts: `solar_1`, `solar_2` (`solar_tracker`), `scanner_1` and `harvester_1` (`grid`), contract `relay_hack` (`relay_hack`).
- Needs: owner go-ahead for `tools/sync_to_game.py apply` (ADR-011, CLAUDE.md), which copies `scripts/libs/` to `lib/` before the machine scripts.
- Pass criteria: no `ImportError`, `ModuleNotFoundError` or "not yet researched" in the log. Scanner prints `<sector>: <name>` lines as before. Harvester moves toward an item, as before.
- Also check: `import heapq` works in harvester_1 (harvester only; documented built-in).

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      | fe9a45c      |        | Pending owner go-ahead for sync. |

## Data Archive persistence (ADR-026, branch feat/data-archive-persistence)

- Needs: Data Archive research (Terraform Index 70,000). Until then `get_component("notebook")` is None and nothing below can be checked.
- Check 1 (scanner): after one full pass, Computer > Data Archive shows `scanner.map` (192 entries) and `scanner.pass` = 1. No per-row saves.
- Check 2 (scanner): a second pass gives `scanner.pass` = 2 and a new map.
- Check 3 (harvester): `harvester.done` appears after the first collect or empty sector, with `"pass"` equal to `scanner.pass`.
- Check 4 (reload): stop and reload the save mid-trip. The harvester does not revisit sectors already in `harvester.done` for the same pass.
- Check 5 (pass reset): after the scanner's next pass, `harvester.done` restarts with the new pass number.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      | fe9a45c      |        | Pending Data Archive research and owner go-ahead for sync. |

## Signal Bus (ADR-028, branch feat/signal-bus-wiring)

- Needs: Signal Bus research. Until then `get_component("comms")` is None and scripts skip all bus calls.
- Check 1 (announce): after one scanner pass, `scan.ready` = 1 and `status.scanner_1` = `{"pass": 1}` in Computer > Signal Bus (Broadcasts).
- Check 2 (heartbeat): `status.harvester_1` shows `{"heat": N}` and changes as heat changes.
- Check 3 (job): from Computer > Signal Bus, queue the plain text `E15` on `jobs.collect` (a scanned sector). The harvester moves toward it when it is reachable this pass, and the message is gone from the queue once taken.
- Check 4 (unreachable job): send `H24` while H24 is not scanned. The message stays queued and the harvester collects its own pick.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      | fe9a45c      |        | Pending Signal Bus research and owner go-ahead for sync. |

## base_watch (Automation, ADR-029, branch feat/base-watch-automation)

- Install: paste `scripts/automations/base_watch.py` into a new Automation (Ship Computer > Automations > + New Automation). Needs Automations research.
- Check 1 (healthy): status bar shows `base ok`; console prints `base ok` once.
- Check 2 (deficit): take a grid into deficit (for example switch off a generator with load on). Console prints `warning: power deficit: net <N> W` once; the status turns to a warning.
- Check 3 (heartbeat): with harvester_1 deployed, stop its script for over 60 game seconds. Console prints `warning: harvester_1: silent for <N> s` once. Restart it, and the line clears to `base ok`.
- Check 4 (bus): Computer > Signal Bus > Broadcasts shows `base.alerts` matching the console alert list.
- Check 5 (imports, UNVERIFIED for automations): the script imports `base_watch` and `power_status` from `lib/`. If the log shows `ImportError` or `ModuleNotFoundError`, Libraries do not work from an Automation; inline the rules or report it.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      | fe9a45c      |        | Pending owner paste and Automations research. Check 5 is the first open question. |

## Full sync, 2026-10-17 (nine conflict files replaced with latest repo versions)

- Game files replaced: harvester_1, o2gen_1, o2gen_2, o2gen_3, pressure_3, relay_hack, solar_1, solar_2, solar_3. Pre-sync copies saved in `.sync-pull/backup-2026-10-17/` (gitignored). `automation_1.py` (base_watch) written.
- Result, from `logs/all.log` (UTC 22:37:57): `scanner_1.py` stopped: `ModuleNotFoundError: No module named 'grid'`. The file `lib/grid.py` exists and matches the repo. Cause not yet known. Possible: the game loads Libraries only at start, so a restart or a Run Script is needed. Next step: restart the game or run `scanner_1` by hand. If `grid` still fails, Library imports do not work at runtime in this build; then inline `grid` into `scanner_1` and `harvester_1` (ADR-025 rollback).

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 22:37Z | fe9a45c | FAIL | scanner_1 `No module named 'grid'`. Pending restart test. |

| 2026-10-17 22:51Z | fe9a45c | FAIL | Restart of scanner_1: same `No module named 'grid'` at line 24. Library imports fail at runtime in this build for this file. Next: inline `grid` (ADR-025 rollback) or check whether the import works in another script. |

## Library imports, after relay_solver rename (ADR-030), 2026-10-18

Libraries created in game by the owner: power_status, solar_tracker, grid, trip_log, job_queue, base_watch, relay_solver.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 23:01Z | fe9a45c | PASS | `relay_hack` contract re-run: `already_completed_correct transmitter.transmit completed with status "already_completed_correct"`. Imports `relay_solver`. |
| 2026-10-17 22:52Z+ | fe9a45c | PASS (no errors) | `scanner_1` (`grid`), `solar_1`, `solar_2`, `solar_3` (`solar_tracker`) restarted by owner. No "Script stopped" lines since. Scanner logs only found items and solar logs nothing, so the log cannot confirm they run; owner reports them running. |
| — | fe9a45c | PENDING | `harvester_1` (`grid`, `job_queue`, `trip_log`): idle, not yet started. |
| — | fe9a45c | PENDING | `automation_1` (`base_watch`, `power_status`): not yet checked in log. |

| 2026-10-17 23:02Z | fe9a45c | PASS (imports) | `automation_1` (base_watch) prints `base ok`, no errors. `base_watch` and `power_status` imports work. Heartbeat path NOT yet confirmed: `base ok` also shows when Signal Bus (`comms`) is not researched, which skips heartbeat checks. Recheck after Signal Bus research. |

## Heartbeat fix (ADR-031), 2026-10-17 night

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-17 23:08Z+ | fe9a45c | PASS (owner) | `pacing` Library present; `scanner_1` restarted on the new code; `harvester_1` and `automation_1` updated. Owner reports base alerts clear. Remaining alert was `power deficit` at night: solar output is zero, so the deficit is expected, not a fault. |

## heater_1 (Heat Generator, spec docs/specs/heater.md, branch feat/heater-controller)

- Where it runs: machine `heater_1` (Mk I Heat Generator). Needs the heater placed and powered.
- Check H-001 (settle time, UNVERIFIED): run the script on a state with a known optimum. Efficiency read one second after each `set_power` should match the value read at once. If not, raise `SETTLE_SECONDS` and log it here.
- Check H-002 (scan): on the first day, the console prints `best power for <state>: <N>` once per state seen. Efficiency then reads 100% at that power. Record the optimum for each state.
- Check H-003 (step size, UNVERIFIED): confirm the peak is hit at a 0.1 step. If `no power reached 100%` appears for a state, probe finer steps by hand and log the value.
- Check H-004 (day change): after midnight, the status line shows the new state and the power changes to that state's value. No scan runs for a state already logged.
- Check H-005 (power off): stop the script. The heater reads power 0.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
| 2026-10-18 | fe9a45c | SYNCED | `heater_1.py` written to the game (owner go-ahead). Replaced the 7-byte "Help me" placeholder. Game file matches repo. Pending a heater placed and the H-001 to H-005 checks. |
| 2026-10-18 | fe9a45c | PASS (H-005) | Owner: script stopped, heater power read 0. H-001 to H-004 still open. |

### PX-001: Control Room API and Signal Bus payload (`scripts/probes/probe_control_room.py`)

- Setup: Control Room open. Signal Bus research done (otherwise the `bus` row is SKIP). Paste the probe as a new card's script on a 2x1 card. Delete the card afterwards.
- Run: the card starts itself. Click empty space on the card once (the `click` row). Read the rows on the card and the console lines `probe <name>: ...`.
- Expected: `widgets` PASS (12 widgets). `persist` PASS on the second tick. `text`, `switch`, `mouse` PASS. `click` PASS after your click. `bus` PASS with sizes 200, 2000, 20000 intact.
- Fail signs: `widgets` FAIL names the widget and the error. Paste the full console output and the card's rows. A `TypeError` means the argument shape guess is wrong: fix the call and record the real shape in `docs/api-notes.md`. If `persist` never passes, the module state does not survive ticks: the probe then re-runs every tick, so stop the card at once.
- Record: the real signatures of each widget that passed, the largest payload that came back intact, and whether `mouse()` returns a position.

| Date | Game version | Result | Notes |
|------|--------------|--------|-------|
|      | fe9a45c      |        |       |
