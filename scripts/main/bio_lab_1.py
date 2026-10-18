"""Bio Lab: analyze collected specimens, buy and stage reagents, extract one sample, ship it.

Where it runs: machine script slot `bio_lab_1` (self = this lab). Home base only: buying,
    stocking and shipping use Inventory, which is available only at Nocturna Base.
Self-contained on purpose (ADR-014): no imports.
Each pass re-reads the machine and takes at most one step (manual "Long-Running Scripts":
    reconciliation loop). Nothing is remembered between passes, so a restart or game load
    resumes from whatever the chamber, input and output hold.
Steps, in order:
    1. Output holds items (samples, or reagents from an unload or discard): send them to
       Inventory. Nothing else starts until the output is empty, so extraction never meets a
       full output.
    2. Chamber empty: eject any staged reagent to Inventory, then take a specimen from
       bio_collector_1.
    3. Specimen collected: analyze it. This reveals the recipe.
    4. Loaded reagents the recipe does not want (a wrong recipe, or a leftover): unload them to
       the output. Extract would destroy them.
    5. Recipe complete: extract, then discard the specimen (ADR-015: one sample per specimen).
    6. Reagent missing: eject any other reagent from the input, load what the input holds, or
       when the input is empty, buy only the shortfall the Inventory lacks and take it into the
       input. Shop purchases land in Inventory, so the buy is followed by the take.
Failed steps are warnings: a transient status ("busy" and similar) retries after
    RETRY_SECONDS; a blocker (no credits, missing collector, refused send) is printed and
    waits PAUSE_SECONDS. The specimen is kept on a blocker, except an unanalyzable one.
API facts relied on (docs/game/biology.md, manual Bio Lab, Shop, Inventory, ports): self.specimen
    (.stage .recipe .fragment_id), self.take_from, self.analyze, self.loaded_reagents, self.load,
    self.unload_reagents, self.extract, self.discard, self.input (connect, take, eject, stacks),
    self.output (connect, send, stacks), shop.buy, inventory.count, get_component, ItemStack
    .id .count .properties, set_status, print, sleep.
"""

PAUSE_SECONDS = 60
RETRY_SECONDS = 5
COLLECTOR_ID = "bio_collector_1"
TRANSIENT = ("busy", "source_busy", "source_changed", "target_changed", "input_occupied")


def first_missing(recipe, loaded):
    for reagent_id in recipe:
        have = loaded.get(reagent_id, 0)
        if have < recipe[reagent_id]:
            return reagent_id, recipe[reagent_id] - have
    return None, 0


def has_excess(recipe, loaded):
    """True when the chamber holds a reagent, or more of one, than the recipe wants."""
    over = [reagent_id for reagent_id in loaded if loaded[reagent_id] > recipe.get(reagent_id, 0)]
    return len(over) > 0


def count_in(stacks, item_id):
    total = 0
    for stack in stacks:
        if stack.id == item_id:
            total += stack.count
    return total


def ship_output():
    """Send every output stack to Inventory. Returns "ok" when the output is empty afterwards."""
    linked = self.output.connect("inventory")
    if linked.status != "ok":
        return linked.status
    for stack in self.output.stacks():
        sent = self.output.send(stack.id, stack.count, stack.properties, "exact")
        if sent.status not in ("ok", "partial"):
            return sent.status
    if len(self.output.stacks()) > 0:
        return "output_not_empty"
    return "ok"


def eject_stray_inputs(keep_id):
    """Eject staged stacks that are not keep_id to Inventory. Returns the first refusal, or "ok".

    Ejected, not flushed: flush destroys the items. Passing "" keeps nothing (idle chamber).
    """
    for stack in self.input.stacks():
        if stack.id != keep_id:
            ejected = self.input.eject(
                "inventory", stack.id, stack.count, stack.properties, "exact"
            )
            if ejected.status not in ("ok", "partial", "no_op"):
                return ejected.status
    return "ok"


def buy_reagent(reagent_id, quantity):
    shop = get_component("shop")
    if shop is None:
        return "shop not found"
    return shop.buy(reagent_id, quantity).status


def blocked(message):
    print("warning: " + message)
    set_status(message, "warn")
    sleep(PAUSE_SECONDS)


def wait(message):
    set_status(message, "info")
    sleep(RETRY_SECONDS)


while True:
    if len(self.output.stacks()) > 0:
        shipped = ship_output()
        if shipped != "ok":
            blocked("output not shipped (" + shipped + ")")
        continue

    specimen = self.specimen
    if specimen is None:
        collector = get_component(COLLECTOR_ID)
        if collector is None:
            blocked(COLLECTOR_ID + " not found")
            continue
        cleared = eject_stray_inputs("")
        if cleared != "ok":
            wait("clearing input: " + cleared)
            continue
        result = self.take_from(collector)
        if result.status == "ok":
            set_status("specimen taken from the collector", "info")
        elif result.status == "source_empty":
            wait("waiting for a specimen")
        elif result.status in TRANSIENT:
            wait("take_from " + result.status)
        else:
            blocked("take_from " + result.status + ": " + result.message)
        continue

    if specimen.stage == "collected":
        analysis = self.analyze()
        if analysis.status == "ok":
            set_status("analyzed " + analysis.info.name, "info")
        elif analysis.status == "busy":
            wait("analyze busy")
        elif analysis.status == "invalid_specimen":
            # Cannot be analyzed, so it would block the chamber forever. Drop it and say why.
            self.discard()
            blocked("specimen cannot be analyzed, discarded")
        else:
            blocked("analyze " + analysis.status + ": " + analysis.message)
        continue

    recipe = specimen.recipe or {}
    loaded = self.loaded_reagents

    if has_excess(recipe, loaded):
        unloaded = self.unload_reagents()
        if unloaded.status in ("ok", "output_full"):
            # output_full leaves some reagents loaded; step 1 ships the output next pass.
            set_status("unloading reagents the recipe does not need", "info")
        elif unloaded.status == "busy":
            wait("unload busy")
        else:
            blocked("unload " + unloaded.status + ": " + unloaded.message)
        continue

    reagent_id, missing = first_missing(recipe, loaded)
    if reagent_id is None:
        extracted = self.extract()
        if extracted.status == "ok":
            # Discard now, while nothing else can start: a restart between the two would
            # extract the same specimen again and spend the reagents twice.
            discarded = self.discard()
            if discarded.status not in ("ok", "input_empty"):
                blocked("discard " + discarded.status + ": " + discarded.message)
            else:
                set_status("sample staged for shipping", "info")
        elif extracted.status in TRANSIENT:
            wait("extract " + extracted.status)
        else:
            blocked("extract " + extracted.status + ": " + extracted.message)
        continue

    cleared = eject_stray_inputs(reagent_id)
    if cleared != "ok":
        wait("clearing input: " + cleared)
        continue

    staged = count_in(self.input.stacks(), reagent_id)
    if staged > 0:
        # Load only what is staged. The input may hold less than the shortfall after a restart.
        loaded_now = self.load(reagent_id, min(missing, staged))
        if loaded_now.status == "ok":
            set_status("loaded " + reagent_id, "info")
        elif loaded_now.status in TRANSIENT:
            wait("load " + reagent_id + " " + loaded_now.status)
        else:
            blocked("load " + reagent_id + ": " + loaded_now.status + ": " + loaded_now.message)
        continue

    inventory = get_component("inventory")
    if inventory is None:
        blocked("inventory not found: the Bio Lab needs home base")
        continue
    in_store = inventory.count(reagent_id)
    if in_store < missing:
        bought = buy_reagent(reagent_id, missing - in_store)
        if bought != "ok":
            blocked("buy " + reagent_id + ": " + bought)
            continue
        set_status("bought " + reagent_id, "info")

    linked = self.input.connect("inventory")
    if linked.status != "ok":
        blocked("input connect: " + linked.status + ": " + linked.message)
        continue
    taken = self.input.take(reagent_id, missing)
    if taken.status in ("ok", "partial") and taken.moved > 0:
        set_status("staging " + reagent_id, "info")
    elif taken.status in TRANSIENT:
        wait("take " + reagent_id + " " + taken.status)
    else:
        blocked("stock " + reagent_id + ": " + taken.status + ": " + taken.message)
