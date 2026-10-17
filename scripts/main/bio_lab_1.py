"""Bio Lab: take a collected specimen, analyze it, stage reagents, extract one sample, ship it.

Where it runs: machine script slot `bio_lab_1` (self = this lab). Home base only for now:
    stocking and shipping use Inventory, which is available only at Nocturna Base.
Self-contained on purpose (ADR-014): no imports.
Method, one specimen at a time:
    1. take the specimen from bio_collector_1 when the chamber is empty;
    2. analyze it (reveals the recipe);
    3. if the output holds anything, ship it to Inventory first. Nothing else starts while the
       output is not empty, so extraction never runs into a full output;
    4. stock each missing reagent from Inventory into self.input, then load what was actually
       moved. The input port holds one reagent type at a time, so any other stack in it is
       ejected to Inventory first;
    5. extract one sample; it lands in the output and is shipped on the next pass;
    6. after a successful ship, discard the specimen unless it is already gone (the game
       reports input_empty for that, which is expected once extraction has used it).
Every blocked step is printed as a warning, at most once per PAUSE_SECONDS, so the log shows
the cause. A refused ship keeps the specimen and the output, and is retried.
API facts relied on (docs/game/biology.md): self.specimen (.stage, .recipe), self.take_from,
    self.analyze, self.loaded_reagents, self.load, self.extract, self.discard, self.input.connect,
    take (.status, .moved), stacks and eject; self.output.connect, stacks and send (.status);
    get_component, ItemStack .id .count .properties, set_status, print, sleep.
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


def clear_input_of(reagent_id):
    """Eject any staged stack that is not the reagent we need, so the input port can latch to it."""
    for stack in self.input.stacks():
        if stack.id != reagent_id:
            ejected = self.input.eject(
                "inventory", stack.id, stack.count, stack.properties, "exact"
            )
            if ejected.status not in ("ok", "partial", "no_op"):
                return ejected.status
    return "ok"


def warn(message):
    print("warning: " + message)
    set_status(message, "warn")


while True:
    specimen = self.specimen
    if specimen is None:
        if collector is None:
            set_status("bio_collector_1 not found", "error")
            sleep(PAUSE_SECONDS)
            continue
        result = self.take_from(collector)
        if result.status != "ok":
            warn("take_from " + result.status)
            sleep(PAUSE_SECONDS)
        continue

    if specimen.stage == "collected":
        analysis = self.analyze()
        if analysis.status != "ok":
            warn("analyze " + analysis.status)
            sleep(PAUSE_SECONDS)
        continue

    if len(self.output.stacks()) > 0:
        shipped = ship_output()
        if shipped == "ok":
            discarded = self.discard()
            if discarded.status not in ("ok", "input_empty"):
                warn("discard " + discarded.status)
            set_status("sample shipped", "info")
        else:
            warn("output not shipped (" + shipped + "), specimen kept")
            sleep(PAUSE_SECONDS)
        continue

    reagent_id, quantity = first_missing(specimen.recipe or {}, self.loaded_reagents)
    if reagent_id is not None:
        self.input.connect("inventory")
        cleared = clear_input_of(reagent_id)
        if cleared != "ok":
            warn("clear input: " + cleared)
            sleep(PAUSE_SECONDS)
            continue
        taken = self.input.take(reagent_id, quantity)
        if taken.status not in ("ok", "partial") or taken.moved < 1:
            warn("stock " + reagent_id + ": " + taken.status)
            sleep(PAUSE_SECONDS)
            continue
        loaded = self.load(reagent_id, taken.moved)
        if loaded.status != "ok":
            warn("load " + reagent_id + ": " + loaded.status)
            sleep(PAUSE_SECONDS)
        continue

    extracted = self.extract()
    if extracted.status != "ok":
        warn("extract " + extracted.status)
        sleep(PAUSE_SECONDS)
        continue
