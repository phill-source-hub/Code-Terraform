# Scanner and Harvester

Source: owner-supplied in-game DOCS text for `scanner_1` and `harvester_1` (build `fe9a45c`). Tag: **VERIFIED (docs)** unless marked UNVERIFIED. Short notes in our own words.

## Scanner (`scanner_1`)

- Scans a sector grid around base. Rows A-H (0-7), columns 1-24 (0-23). Base is **E13**. Full grid A1-H24 (192 sectors).
- `self.scan(sector)`: self-only, timed. Returns ScanResult with `.status`, `.message`, `.id`, `.name`, `.value`.
- `status` `"ok"`: an item is there. `"empty"`: completed scan, no item. Malformed sector ids raise `ValueError`.
- Build sector names with `chr(65 + row) + str(col + 1)` (`chr(65)` is `A`).
- `get_component("scanner_1").get_scanned()`: snapshot dict of sector id to ScanResult. Re-call it in loops; an old dict does not update.

## Harvester (`harvester_1`)

- Collects surface items. The harvester has its own in-built battery, separate from the base battery. It has no power logic.
- `self.move(sector)`: one cardinal cell per call. Statuses: `ok`, `invalid`, `too_far`, `already_here`, `overheated`, `moving`, `busy`.
- `self.collect()`: returns ScanResult. Statuses: `ok` (item payload), `empty`, `holding`, `overheated`, `moving`, `collecting`, `busy`.
- Collected items go to the harvester's single **held slot**, not Inventory. `self.store()` moves the held item to Inventory from any sector: returns ItemResult with `.item_id` after `ok`.
- Selling is from the Shop: `shop.sell(item_id, quantity)`. Surface finds (Soil Sample 50 cr up to Exotic Compound 5,000 cr) are cargo to sell.
- **Heat** (VERIFIED docs): move to a sector with an item +1; move to an empty sector +7; collect from an empty sector +9; each hour -3. Max 100. `self.get_heat()` reads it. Use `sleep()` for cooling time.
- Plants field work (`load_seed`, `plant`, `harvest`, etc.) is not used yet.

## Our assumptions (UNVERIFIED in game)

- Position: the script reads `self.get_position()` every pass (manual: current sector id). It assumes nothing about the start cell, since a new save or later game state may differ.
- Held item: `self.get_held()` is read every pass; a held item is stored first (manual: empty string when the slot is empty).
- Hour-long cooling uses `clock.real_seconds_per_hour()`. Sleep units are game seconds (see `docs/api-notes.md`).
- Scanner does one snake pass over all 192 sectors and saves the result to the Data Archive key `scanner.map` (superseded the harvester-centred scan, ADR-021). It repeats each world hour. The manual does not say whether sectors refill.
