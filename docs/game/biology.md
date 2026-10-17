# Biology: Bio Collector, Bio Lab, Bio Exchange

Source: in-game DOCS manual, build `fe9a45c`. Sections: "Bio Collector", "Bio Lab", "Bio Exchange", "First Biology Loop", types `FragmentLocation`, `Specimen`, `AnalyzeResult`, `AnalyzeInfo`, `BioOrder`. Tag: **VERIFIED (docs)** unless marked. Short notes in our own words.

## Prerequisites (all three)

- Power: each machine draws a few watts (Collector -5 W, Lab -5 W, Exchange -8 W). They are unpowered in this save at the time of writing (fleet file).
- Scripted item transfers need **Auto Feeders** research. Manual Biology buttons do not.
- Reagents: five Lab reagents are sold in the Shop's Biology category. Shop buys go to base Inventory, so the Lab needs them in home Inventory.
- Home base (`outpost_home`, Nocturna Base) is the only place where Inventory connects to a machine.
- Costs: Collector 3,000 cr, Lab 5,000 cr, Exchange 4,000 cr.

## Bio Collector (`bio_collector_1`)

- `self.scan()` → list[FragmentLocation], nearest first. Fields: `coords` (list[float]), `distance`, `cataloged` (bool), and once cataloged `fragment_id`, `name`, `rarity`. Unknown ones have `None`.
- `self.collect(coords)` (self only), trip about 0.1-0.3 h, script pauses. Statuses: `ok`, `busy` (transient), `cargo_occupied`, `invalid_coords`, `no_fragment`.
- `self.cargo`: Specimen or None. Cleared when a Lab takes it.
- `self.discard()` (self only): drops the cargo specimen. Statuses: `ok`, `empty`, `busy`.

## Bio Lab (`bio_lab_1`)

- `self.specimen`: Specimen or None. `.stage` is `"collected"` then `"analyzed"`. After analysis `.fragment_id`, `.rarity`, `.recipe` (dict[str, int]) are set.
- `self.take_from(collector)` (self only): pulls cargo from a same-outpost collector. Statuses: `ok`, `busy`, `input_occupied`, `not_found`, `source_empty`, `source_busy`, `wrong_outpost`, `invalid_source`, `output_full`.
- `self.analyze()` (self only), about 0.1 h. Returns AnalyzeResult: `.status` (`ok`, `busy`, `input_empty`, `invalid_specimen`, `output_full`), `.message`, `.info` (AnalyzeInfo after ok: `fragment_id`, `name`, `rarity`, `required_recipe`, `coords`, `distance`). Adds the fragment to the Journal.
- `self.loaded_reagents`: dict[str, int] staged for `extract()`.
- `self.input` (InputSlot): one reagent id at a time, latched until `load()` consumes it or `flush()`. Connect `"inventory"` only at Nocturna Base.
- `self.load(reagent_id, qty)` (self only): consumes from `self.input`. Statuses: `ok`, `busy`, `invalid_reagent`, `invalid_qty`, `insufficient_input`, `output_full`.
- `self.extract()` (self only), about 0.1 + 0.05 × units h. Consumes `loaded_reagents`, stages 1 sample in `self.output`. Statuses: `ok`, `output_full` (keeps the work), `recipe_mismatch` (destroys reagents, keeps specimen), `busy`, `input_empty`, `not_analyzed`, `invalid_specimen`.
- `self.output` (OutputSlot): 30 units, shared by samples and unloaded reagents. Connect local storage, then `send(item_id, count, properties, mode)`.
- `self.discard()` (self only): drops the specimen and stages loaded reagents in output. Statuses: `ok`, `input_empty`, `busy`, `output_full`.
- `self.unload_reagents()` (self only): stages loaded reagents back in output.

**Open question (ours, not in the manual):** whether a specimen can give more than one sample. The manual does not say. Our script discards the specimen after each successful extract (one sample per specimen). Check in game.

## Bio Exchange (`bio_exchange_1`)

- `self.orders()` → list[BioOrder]. Fields: `id`, `name`, `biome`, `requires` (dict[str, int]), `reward`, `status` (`available`, `active`, `complete`), `delivered`, `in_transit`, `percent`, `target_glow`. Progress is shared by all Exchanges on the order.
- `self.active_order()` → BioOrder or None. Snapshot. Re-query for fresh progress.
- `self.set_order(order_id)` (self only). Statuses: `ok`, `unknown_order`, `completed`.
- `self.clear_order()` (self only). Progress is kept. Statuses: `ok`, `busy`, `output_full`.
- `self.matches_order(item_id, properties)` → bool. Checks one exact item (id and properties from an ItemStack) against the active order's requirement, without moving it.
- `self.input` (InputSlot): 10 units, one item id at a time. Connect Inventory at home.
- `self.deliver()` (self only). Moves one sample toward the order. Statuses: `ok`, `complete` (order filled, reward paid), `no_input`, `output_full`, `no_active`, `busy`.
- `self.output` (OutputSlot): receives a surplus sample when another Exchange finishes the order first.
- `self.lifetime_credits()` → int.

## Items and fragments

- `FragmentLocation.fragment_id` values seen in the manual include `gw_cranial_plate`, `gw_caudal_fin`, `gw_cardiac_node`, `gw_jaw_fang`, `gw_spinal_vertebra`, `vc_dorsal_carapace`, `vc_mandible_claw`, `vc_antenna_cluster`, `vc_walking_leg`, `vc_eye_stalk`, `oc_cranium` (list truncated in the manual).
- Rarity: `common`, `uncommon`, `rare`, `legendary`. Biome: `frozen`, `coastal`, `geothermal`, `volcanic`, `deep`.
- A Creature's entry appears in `journal.cataloged_creatures(planet_id)` after all five of its fragments are analyzed.

## Our assumptions (UNVERIFIED in game)

- `inventory.stacks()` exists on the Inventory component. The manual mentions `stacks()` on Inventory, Storage Bin and Warehouse, but the Inventory method is not shown in the extract.
- `exchange.active_order()` and `exchange.orders()` can be called from another script. The manual says other scripts can read public state. Confirm in game.
- Each Lab sample is one per specimen (see above).
- Reagent ids come from `specimen.recipe` keys. Their ids are not hardcoded.
