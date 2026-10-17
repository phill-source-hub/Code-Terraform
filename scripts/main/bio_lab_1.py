"""Bio Lab: take a collected specimen, analyze it, stage reagents, extract one sample, ship it.

Where it runs: machine script slot `bio_lab_1` (self = this lab). Home base only for now:
    stocking and shipping use Inventory, which is available only at Nocturna Base.
Self-contained on purpose (ADR-014): no imports.
Method, one specimen at a time:
    1. take the specimen from bio_collector_1 when the chamber is empty;
    2. analyze it (reveals the recipe);
    3. take each missing reagent from Inventory into self.input, then load it;
    4. extract one sample; ship every stack in self.output to Inventory;
    5. discard the specimen so the chamber is free for the next one. ASSUMPTION: one sample per
       specimen. The manual does not say a specimen is used up. Check in game.
Restart-safe: every pass re-reads the chamber and loaded_reagents, so a restart resumes the step.
Waiting: analyze and extract are timed, so the loop yields. PAUSE_SECONDS is used after a
    blocked status (no input, output full, busy).
API facts relied on (docs/game/biology.md): self.specimen (.stage, .recipe), self.take_from,
    self.analyze, self.loaded_reagents, self.load, self.extract, self.discard, self.input.connect
    and take, self.output.connect, send and stacks, get_component, ItemStack .id .count
    .properties, set_status.
"""

PAUSE_SECONDS = 60

collector = get_component("bio_collector_1")


def first_missing(recipe, loaded):
    for reagent_id, quantity in recipe.items():
        have = loaded.get(reagent_id, 0)
        if have < quantity:
            return reagent_id, quantity - have
    return None, 0


while True:
    specimen = self.specimen
    if specimen is None:
        if collector is None:
            set_status("bio_collector_1 not found", "error")
            sleep(PAUSE_SECONDS)
            continue
        result = self.take_from(collector)
        if result.status != "ok":
            set_status("take_from " + result.status, "info")
            sleep(PAUSE_SECONDS)
        continue

    if specimen.stage == "collected":
        analysis = self.analyze()
        if analysis.status != "ok":
            set_status("analyze " + analysis.status, "warn")
            sleep(PAUSE_SECONDS)
        continue

    reagent_id, quantity = first_missing(specimen.recipe or {}, self.loaded_reagents)
    if reagent_id is not None:
        self.input.connect("inventory")
        taken = self.input.take(reagent_id, quantity)
        if taken.status not in ("ok", "partial"):
            set_status("stock " + reagent_id + ": " + taken.status, "warn")
            sleep(PAUSE_SECONDS)
            continue
        loaded = self.load(reagent_id, quantity)
        if loaded.status != "ok":
            set_status("load " + loaded.status, "warn")
            sleep(PAUSE_SECONDS)
        continue

    extracted = self.extract()
    if extracted.status != "ok":
        set_status("extract " + extracted.status, "warn")
        sleep(PAUSE_SECONDS)
        continue
    self.output.connect("inventory")
    for stack in self.output.stacks():
        self.output.send(stack.id, stack.count, stack.properties, "exact")
    self.discard()
    set_status("sample shipped", "info")
