"""Bio Lab: take a collected specimen, analyze it, stage reagents, extract one sample, ship it.

Where it runs: machine script slot `bio_lab_1` (self = this lab). Home base only for now:
    stocking and shipping use Inventory, which is available only at Nocturna Base.
Self-contained on purpose (ADR-014): no imports.
Method, one specimen at a time:
    1. take the specimen from bio_collector_1 when the chamber is empty;
    2. analyze it (reveals the recipe);
    3. if the output holds anything, ship it to Inventory first. Nothing else starts while the
       output is not empty, so extraction never runs into a full output;
    4. take each missing reagent from Inventory into self.input, then load it;
    5. extract one sample; it lands in the output and is shipped on the next pass;
    6. once the output is empty after a successful ship, discard the specimen. ASSUMPTION: one
       sample per specimen. The manual does not say a specimen is used up. Check in game.
A ship that fails (for example, Auto Feeders is not researched and send reports
research_required) keeps the specimen and the output. The script warns and retries each
PAUSE_SECONDS. Nothing is discarded that has not been shipped.
Restart-safe: every pass re-reads the chamber, the output and loaded_reagents.
API facts relied on (docs/game/biology.md): self.specimen (.stage, .recipe), self.take_from,
    self.analyze, self.loaded_reagents, self.load, self.extract, self.discard, self.input.connect
    and take, self.output.connect, stacks and send (.status), get_component, ItemStack .id
    .count .properties, set_status, print, sleep.
"""

PAUSE_SECONDS = 60

collector = get_component("bio_collector_1")


def first_missing(recipe, loaded):
    for reagent_id, quantity in recipe.items():
        have = loaded.get(reagent_id, 0)
        if have < quantity:
            return reagent_id, quantity - have
    return None, 0


def ship_output():
    """Send every output stack to Inventory. Returns "ok" when the output is empty afterwards."""
    self.output.connect("inventory")
    for stack in self.output.stacks():
        sent = self.output.send(stack.id, stack.count, stack.properties, "exact")
        if sent.status not in ("ok", "partial"):
            return sent.status
    if len(self.output.stacks()) > 0:
        return "output_not_empty"
    return "ok"


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

    if len(self.output.stacks()) > 0:
        shipped = ship_output()
        if shipped == "ok":
            self.discard()
            set_status("sample shipped", "info")
        else:
            print("warning: output not shipped (" + shipped + "), specimen kept")
            set_status("output not shipped: " + shipped, "warn")
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
