# Spec: Control Room cards (dashboards and controls)

Status: draft for owner review. Not started. Source: owner brief (Control Room page), manual extracts in `docs/game/` (power, rover, drone, signal bus, shop) and manual pages (Earth Orders, Storage Bin, Atmosphere, Map Markers, Supply Dock, Weather Station, Drone Service Station).

Tags: **VERIFIED (docs)** = in our extracts or manual. **UNVERIFIED** = from the owner's brief text only, or not yet in `docs/api-notes.md`. UNVERIFIED names need a probe card (step 0) before any code relies on them.

## Shared rules (all cards)

- **Read-only first.** Dashboards only read. Control cards write only through shared authorities (`power_control`, `shop`, `comms`, `computer`). Cards never call a machine's self method.
- **Rover, station and dock commands go through the Signal Bus.** The card sends a message. The target machine's own script receives it, checks it, and acts. Machine scripts and their receive loops are a separate piece of work per card (marked "receiver").
- **Channel names:** `ctrl.<target_id>.<verb>`, e.g. `ctrl.rover_1.dispatch`. Ack channel: `ctrl.ack.<target_id>`. Status is a broadcast (`latest_info`), not a queue.
- **Message shape:** a small dict with `req` (request id, from the card's counter), `verb`, and args. Keep it under the size the bus allows (**UNVERIFIED**, probe).
- **Every write shows its result.** Read the `ActionResult` / `SaleResult` / `SendResult` status literal and show it. Never assume success.
- **Irreversible actions** (sell, undeploy, decommission) use two steps: button arms, a second button confirms. Arming times out after 5 s.
- **Drawing:** `panel.clear()` at the top of each loop. Keep layouts relative to `panel.width()` / `panel.height()`. Stored widget keys stay well under the 512-per-card cap.
- **Logic vs adapter:** pure functions (threshold, runway, sort, message build) in `scripts/libs/` with no game calls. Card script is a thin adapter. Logic gets unit tests (house rule).
- **Scope:** each card = one card script plus its logic module and tests. Receivers are separate and listed under each card.

---

## Step 0. Probe card (first, UNVERIFIED facts)

- **Goal:** confirm the Control Room API and the bus payload before any build.
- **Size:** 1×1, throwaway. Lives in the Control Room only during the probe; deleted after.
- **Checks:**
  - `panel.clear`, `draw_text`, `progress_bar`, `status_dot`, `button`, `switch`, `combo`, `text_field` each exist and draw.
  - `mouse()` and `clicks()` return what the brief says.
  - `set_text` / `get_text` round trip on a `text_field`.
  - `comms.send` accepts a dict payload; `receive` returns it intact.
  - Max payload size on the bus (send a long string, read back).
  - Stored keys: count reads after 50 widgets.
- **Output:** `docs/in-game-test-log.md` rows (H-series), and the verified facts copied into `docs/api-notes.md` with evidence.
- **Tests:** none (game-only). Logged as in-game checklist rows.
- **Exit criteria:** all checks pass or the failing one is written down with a fallback. If `combo` / `text_field` misbehave, the control cards use buttons only.

---

## Dashboards (read-only)

### D1. Base overview (2×2)

- **Goal:** one screen for the base: power net, O₂/N₂/pressure, fleet dots, Earth Orders progress, alert strip.
- **Reads:** `power_control.total()`, `get_component("atmosphere")` (`get_o2`, `get_n2`, `get_pressure`), `fleet.mobile_units()`, `orders.list_orders()`. Alert strip uses the same thresholds as D2, D3, D4, D6. **VERIFIED (docs)** for all.
- **Layout:** top band = alert strip; left = power and atmosphere bars; right = fleet dots and order list.
- **Logic module:** `scripts/libs/control_room/overview.py` — builds rows from snapshot dicts, picks alert level.
- **States:** missing sensor (O₂ / pressure need repaired sensors) shows "no sensor", not 0.
- **Tests:** row building with full, empty and missing-sensor inputs; alert level per threshold.
- **Done when:** values match the source panels in game for 5 ticks; no flicker.

### D2. Power runway gauge (1×1 each grid)

- **Goal:** show how long each grid runs on storage.
- **Reads:** `power_control.grids()` → `net`, `stored`, `reserve_stored`, `has_generator`. **VERIFIED (docs)**.
- **Logic:** `runway_h = (stored + reserve_stored) / -net` when `net < 0`; `inf` otherwise. Colour: green > 2 h, yellow 1–2 h (the manual's one-hour recovery rule sits at 1 h), red < 1 h.
- **Layout:** one gauge per grid, grid anchor id as label. Max 4 gauges on one card, extra grids listed as text.
- **Tests:** runway math (net positive, net zero, net negative, zero stored, reserve only); colour bands at the boundaries.
- **Done when:** runway matches hand calculation in game for one grid.

### D3. Fleet board (2×1)

- **Goal:** one row per vehicle and drone.
- **Reads:** `fleet.vehicles()`, `fleet.drones()`: `status`, `battery_level`, `oil_level`, `rescue_status`, `is_being_rescued`, `current_station`. **VERIFIED (docs)**.
- **Layout:** row = status dot + name + status text + battery bar. Red dot: `stranded`, `stalled_no_battery`, `stalled_no_oil`, `scrambled`. Yellow: `waiting_*`, `holding_weather`, `being_rescued`. Green: otherwise.
- **Logic:** `scripts/libs/control_room/fleet_rows.py` — status → colour; sort: red first, then name.
- **Tests:** colour map for every status literal in the manual list; sort order; drone with `oil_level` vs `battery_level` chooses the right bar (check `engine`).
- **Done when:** a mixed fleet shows heli and electric rows correctly.

### D4. Drone exposure monitor (1×1)

- **Goal:** warn before a drone scrambles from Raw Uranium.
- **Reads:** per drone `get_component(id).exposure()` and `exposure_capacity()` (100). Drone list from `fleet.drones()`. **VERIFIED (docs)**.
- **Logic:** percent = exposure / capacity. Yellow ≥ 60%, red ≥ 80%. Show `is_plated()` so the owner knows a plated drone takes no Raw Uranium exposure.
- **Safety note on card:** text line "Raw Uranium: 40 per batch unplated".
- **Tests:** percent and band at boundaries; plated flag shown.
- **Done when:** exposure bar moves after a collect in game.

### D5. Charging queue board (1×2)

- **Goal:** what is waiting at each charger and station, and at what rate.
- **Reads:** Battery Charger `get_queue()`, `get_active()`, `get_charge_rate(slot)`; Drone Service Station `get_active()`, `get_queue()`, `get_charge_rate(id)`. **VERIFIED (docs)**.
- **Layout:** one block per machine: active list, queue list, rate. Empty = "idle" text.
- **Tests:** list formatting for empty / active / queued; rate sum.
- **Done when:** queue order matches the machine in game.

### D6. Earth Orders tracker (2×1)

- **Goal:** progress on current orders and a "next up" list.
- **Reads:** `orders.list_orders()` (current), `list_upcoming_orders()` (future). `Order` fields: check the manual `Order` entry before coding (**UNVERIFIED** field names until read). Manual page 192 is the source.
- **Layout:** left = current orders with progress bars; right = next 3 upcoming.
- **Action:** the orders list is read-only. Scripts cannot create or cancel orders (manual).
- **Tests:** progress fraction with zero target guarded; empty list shows "no contractor shipment".
- **Done when:** progress matches the in-game order panel.

### D7. Atmosphere history (1×2)

- **Goal:** O₂, N₂, pressure bars and a 50-tick spark line each.
- **Reads:** `atmosphere.get_o2()`, `get_n2()`, `get_pressure()`, `get_co2()`. **VERIFIED (docs)**; O₂ and pressure need repaired sensors.
- **Logic:** `scripts/libs/control_room/history.py` — ring buffer of 50 floats, reset on card restart. The buffer is in Python memory, not stored keys.
- **Tests:** ring buffer wrap, min/max scale, first-tick (fewer than 50 samples) draw.
- **Done when:** spark line shows 50 ticks and then scrolls.

### D8. Storage inventory (2×2)

- **Goal:** every storage bin, Warehouse and Lead Cask: icon, name, fill %, count.
- **Reads:** Storage Bin `count(item_id)`, `get_capacity()`. Warehouse and Lead Cask `count(item_id)` (manual says same query). Find bins via `outpost.buildings()` (**UNVERIFIED** exact query; check Storage Bin manual page). Bin with a latched item shows the item; empty shows "empty".
- **Tests:** fill % with capacity 0 guarded; latched vs empty display.
- **Done when:** counts match Inventory for one bin.

### D9. Signal Bus monitor (2×1)

- **Goal:** live view of channels and last broadcasts. The debug view for all control cards.
- **Reads:** `comms.pending(channel)` for a channel list held in the card's config (one saved combo key), `comms.latest_info(channel)`. **VERIFIED (docs)** for names; the channel list is owner-set.
- **Layout:** channel combo, pending list (id, sender, tick, value), latest value box.
- **Tests:** pending list formatting; empty channel.
- **Done when:** a test `send` from the probe card shows here.

### D10. Dark-outpost diagnostics (1×1)

- **Goal:** explain why an outpost has no power.
- **Reads:** `power_control.grid(target_id)`, `is_powered(machine_id)`, `grid.generated`, `consumed`, `net`, `has_generator`. **VERIFIED (docs)**.
- **Logic:** reasons in order: no grid (`None`), grid has no generator, net < 0 with stored 0, else "unknown — check wire pieces and bridges" (manual checklist).
- **Tests:** each reason branch; the check order.
- **Done when:** a known dark outpost gets the expected reason.

---

## Control cards (write actions)

### C1. Breaker panel (2×2)

- **Goal:** on/off per machine from the card.
- **Authority:** `power_control.set_powered(id, on)`; `can_power_off(id)` decides if the toggle shows. **VERIFIED (docs)**.
- **UI:** one `switch` per machine (up to 12 per 2×2 card; paging via a radio group if more). Status line shows the last `set_powered` status: `ok`, `not_found`, `not_toggleable`, `under_construction`, `not_connected`, `not_enough_power`.
- **Behaviour:** switch state comes from `is_powered(id)`. The card sets the switch, not the grid, so a click that fails snaps back.
- **Guard:** a machine with `can_power_off` false is greyed out with a reason.
- **Tests:** status-to-message map; toggle state sync; greyed-out rule.
- **Receiver:** none.
- **Done when:** toggling a smelter in game pauses and resumes it; the status line shows `not_enough_power` when expected.

### C2. Load-shed presets (1×1)

- **Goal:** one click sheds non-essential load; one click restores.
- **Authority:** `power_control.set_powered` on a named list per preset. **VERIFIED (docs)**.
- **Presets:** owner-defined, saved in one stored key as JSON text. Default: "Night saver" (lists empty until owner fills them).
- **Behaviour:** "Shed" turns off the listed machines in list order and stops on the first non-`ok` status (shows it). "Restore" turns back on only the machines the preset turned off (remembered in the card's stored key), not manual-off machines.
- **Tests:** shed order, stop-on-error, restore only the card's own switches, preset parse of bad JSON (falls back to empty).
- **Receiver:** none.
- **Done when:** shed then restore returns the same state; manual-off machine stays off.

### C3. Rover dispatch: "send rover X to nearest Y deposit" (2×1)

- **Goal:** pick a rover and a resource, send it to the nearest known deposit.
- **Card side:** rover combo (ids from `fleet.vehicles()` filtered to rovers), resource combo (owner list), `Send` button. Sends `ctrl.<rover>.dispatch` with `{req, verb: "nearest", resource}`. Shows ack from `ctrl.ack.<rover>` matching `req`.
- **Receiver (rover script, separate piece):** loop reads `comms.receive("ctrl.rover_1.dispatch")`, checks battery (`level()` ≥ 0.3 or refuses with `low_battery`), then `sonar.scan()`, picks nearest matching site by `get_distance_to`, `survey(site)`, `set_target`, `brake()` on arrival before `mine()`. Writes status to a broadcast channel `ctrl.status.<rover>`.
- **Bounds:** the receiver loop has a sleep and a max-wait per task; a stuck task reports `timeout` and stops the rover.
- **Logic (card):** `scripts/libs/control_room/dispatch.py` — build message, match ack by `req`, timeout to "no answer" after N ticks.
- **Logic (receiver):** `scripts/libs/rover_dispatch.py` — pick nearest site (pure, given site list and rover position); unit tested.
- **Tests:** message build; ack match; timeout; nearest-site pick with ties (alphabetical id, same as the dock rule in manual); low-battery refusal.
- **Pre-req:** Signal Bus research; probe step 0 confirms payload. Rover script edits go through the project's game-script workflow (owner go-ahead for sync to game folder).
- **Done when:** card sends, rover scans, travels, mines, reports; ack and status show on the card.

### C4. Rover rescue button (1×1)

- **Goal:** rescue a stranded rover from a station.
- **Card side:** lists rovers with `status() == "stranded"` (from `fleet.vehicles()`). Target-level slider (0–1). Button sends `ctrl.<station>.rescue` with `{vehicle, target}`.
- **Receiver (station script):** calls `self.dispatch_rescue(vehicle_name, target)` if `not self.is_rescuing()`; reports the status literal on `ctrl.status.<station>`. Statuses per manual: `ok`, `already_dispatched`, `station_offline`, `not_found`, `invalid`.
- **Tests:** card button enabled only for stranded rovers; receiver guard; status map.
- **Note:** `dispatch_rescue` exists on both Vehicle Charging Station and Drone Service Station (manual open question). Receiver for vehicles uses the Vehicle Charging Station entry only.
- **Done when:** a stranded rover in game is recovered and the card shows the result.

### C5. Charge-to-level queue (1×2)

- **Goal:** queue a charge to a set level for a vehicle at a station.
- **Card side:** vehicle combo, target slider (0–100%), `Queue` button → `ctrl.<station>.charge` with `{vehicle, target}`. Shows the station's queue position from D5 data.
- **Receiver (station script):** `self.charge(vehicle_id, target)`; statuses `queued`, `target_reached`, `not_docked` etc. per manual. Repeat calls update target without reordering (manual).
- **Tests:** target clamp to (0, 1]; status map; queue position lookup.
- **Done when:** a docked rover charges to the chosen level in game.

### C6. Sell surplus (1×1)

- **Goal:** sell a set quantity of an item.
- **Authority:** `shop.sell(item_id, quantity)`. Result fields `.status`, `.message`, success `.item_id`, `.units`, `.credits`. **VERIFIED (docs)**.
- **UI:** item combo (owner list), quantity text_field (whole number ≥ 1), `Arm` → `Confirm` two-step (5 s timeout). Result line shows units and credits.
- **Guard:** quantity parse rejects non-integers and ≤ 0; card shows the Inventory count before arming (`inventory` authority, check manual entry first).
- **Tests:** quantity parse; arm timeout; result formatting.
- **Receiver:** none.
- **Done when:** a sale in game shows the right units and credits; a too-big quantity shows the refusal status.

### C7. Supply Dock assigner (2×1)

- **Goal:** assign a current Earth order to a Supply Dock.
- **Card side:** dock combo (`get_component` ids of Supply Docks), order combo from `orders.list_orders()`, `Assign` button → `ctrl.<dock>.assign` with `{order_id}`.
- **Receiver (dock script):** owns `input.connect` / `take` for the order, `clear_order()` on change. Reports status on `ctrl.status.<dock>`.
- **Note:** dock API details (assignment method names) are only partly in the manual extract (page 194). Read the full dock page before the receiver is written. Mark assignment method UNVERIFIED until then.
- **Tests:** order combo filters out completed orders; assign message build; receiver logic in libs.
- **Done when:** a dock assigned in the card ships the order items.

### C8. Comms console (2×1)

- **Goal:** send any message to any channel and read back the queue. Test tool.
- **Authority:** `comms.send(channel, value)`, `pending(channel)`, `latest(channel)`. Result `SendResult` `.status`, `.message_id`. **VERIFIED (docs)**; payload type UNVERIFIED (probe).
- **UI:** channel text_field, value text_field, `Send` button, `Cancel` for a `message_id` (`comms.cancel` **UNVERIFIED** name; check bus page), recent list from D9.
- **Guard:** channel must match the `ctrl.` prefix, or the owner ticks "any channel" (a checkbox). Stops accidents.
- **Tests:** channel validation; message id kept for cancel.
- **Done when:** send, see it in pending, cancel it.

### C9. Mission presets (2×1)

- **Goal:** one click runs a bundle: "Dust storm", "Dispatch rovers", "Night".
- **Card side:** radio group of presets. Each preset is a list of steps: breaker changes (C1 authority), bus messages (C3/C4/C5 format), solar tilt request. Run shows each step's status, stops on first refusal.
- **Logic:** `scripts/libs/control_room/presets.py` — preset table, step runner (pure). Table is data, tested.
- **Tests:** step order; stop on refusal; unknown preset rejected; each preset validates against the step schema.
- **Dependency:** C1, C3 or C5 must exist first. Build last of the controls.
- **Done when:** a preset runs its steps in game and reports each result.

### C10. Computer deploy / undeploy (1×1)

- **Goal:** deploy or undeploy a machine from the card. Lowest priority, highest risk.
- **Authority:** `computer.deploy()`, `undeploy()`, `decommission()`, `rename()` (**UNVERIFIED** signatures; read the Ship Computer manual page `206-ship-computer.md` first).
- **UI:** combo of targets, action radio (rename / deploy / undeploy / decommission), `checkbox` "I know this is irreversible" required for undeploy and decommission, two-step confirm.
- **Guard:** decommission is never on a preset. Rename only is the default.
- **Tests:** guard logic (checkbox required; rename does not need it).
- **Done when:** rename works in game; the destructive path is tested only on a throwaway machine the owner names.

---

## Build order (agreed)

0. Probe card (step 0).
1. Read-only set: D2 power runway, D3 fleet, D6 Earth Orders, D9 Signal Bus monitor, then D1 base overview (uses D2 / D3 / D6 logic).
2. C1 breaker panel (direct authority, no receiver).
3. C3 rover dispatch (card + rover receiver). Biggest piece.

Items after 3 (C2, C4–C10, D4, D5, D7, D8, D10) are planned here but get their own go-ahead.

## Open questions (owner)

- Which machines are "non-essential" for C2 presets.
- Deposit list for C3: from the Data Archive, a scan result, or a fixed list the owner types? Default if no answer: rover's own sonar scan.
- Rover low-battery cutoff for C3 (default 0.3).
- Whether C8 may send to non-`ctrl.` channels.
- Receiver scripts go through the owner's sync go-ahead (`tools/sync_to_game.py apply`), per project rules.
