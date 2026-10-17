"""Bio Exchange: fill one Bio Order from samples held in Inventory (home base).

Where it runs: machine script slot `bio_exchange_1` (self = this exchange). Home base only:
    samples come from Inventory, available only at Nocturna Base.
Self-contained on purpose (ADR-014): no imports.
Method: assign the first Bio Order that is not complete. Each pass finds one Inventory sample
    that matches the active order (matches_order), takes it into self.input, and delivers it.
    deliver() reports progress and completion through its status.
Waiting: deliver() is short but the loop yields. PAUSE_SECONDS is used after a blocked status or
    when no sample is waiting.
API facts relied on (docs/game/biology.md): self.orders(), self.set_order, self.active_order(),
    self.clear_order, self.matches_order, self.input.connect and take, self.deliver,
    get_component, inventory.stacks(), ItemStack .id .count .properties, set_status.
"""

PAUSE_SECONDS = 60

inventory = get_component("inventory")
self.input.connect("inventory")


def first_open_order(orders):
    for order in orders:
        if order.status != "complete":
            return order.id
    return None


def find_matching_sample(exchange, stacks):
    for stack in stacks:
        if stack.count > 0 and exchange.matches_order(stack.id, stack.properties):
            return stack
    return None


while True:
    order = self.active_order()
    if order is None:
        order_id = first_open_order(self.orders())
        if order_id is None:
            set_status("no open bio orders", "info")
            sleep(PAUSE_SECONDS)
            continue
        assigned = self.set_order(order_id)
        if assigned.status != "ok":
            set_status("set_order " + assigned.status, "warn")
            sleep(PAUSE_SECONDS)
        continue

    if order.status == "complete":
        self.clear_order()
        continue

    sample = find_matching_sample(self, inventory.stacks())
    if sample is None:
        set_status("waiting for samples", "info")
        sleep(PAUSE_SECONDS)
        continue

    taken = self.input.take(sample.id, 1, sample.properties, "exact")
    if taken.status not in ("ok", "partial"):
        set_status("take " + taken.status, "warn")
        sleep(PAUSE_SECONDS)
        continue

    delivered = self.deliver()
    if delivered.status == "complete":
        set_status("order complete", "info")
        sleep(PAUSE_SECONDS)
    elif delivered.status != "ok":
        set_status("deliver " + delivered.status, "warn")
        sleep(PAUSE_SECONDS)
