"""Bio Exchange: fill open Bio Orders from samples held in Inventory (home base).

Where it runs: machine script slot `bio_exchange_1` (self = this exchange). Home base only:
    samples come from Inventory, available only at Nocturna Base.
Self-contained on purpose (ADR-014): no imports.
Each pass re-reads the machine and takes at most one step, so a restart resumes from whatever
    the input and output hold (manual "Long-Running Scripts"). Samples are never flushed:
    anything not wanted goes back to Inventory.
Steps, in order:
    1. Output holds items (a surplus refunded when another Exchange finished the order first):
       send them to Inventory. Nothing else starts until the output is empty.
    2. No open order is assigned, or the assigned one is complete: clear a complete order,
       eject staged samples, then assign an open order. Each candidate is tried with set_order
       and kept only when matches_order accepts a sample in Inventory. An order that needs a
       variant this Exchange cannot make (a glow or gene requirement) is cleared again.
    3. Input holds a sample the active order does not accept: eject it to Inventory.
    4. Input holds a sample the active order accepts: deliver() one.
    5. Inventory holds a sample the order still needs: take it into the input. The take is
       capped by what is still needed after samples already staged, and by the input size.
Multiple required fragments: each sample is checked against the whole order (matches_order),
    and the still-needed count is per fragment, so every requirement is served.
API facts relied on (docs/game/biology.md, manual Bio Exchange and BioOrder): self.orders(),
    self.active_order(), self.set_order, self.clear_order, self.matches_order, self.deliver,
    self.input (connect, take, eject, stacks), self.output (send, stacks), BioOrder .id .name
    .status .requires .delivered .in_transit, inventory.stacks(), ItemStack .id .count
    .properties, get_component, set_status, print, sleep.
"""

PAUSE_SECONDS = 60
RETRY_SECONDS = 5
INPUT_CAPACITY = 10
# no_input is not transient: the input lists a sample that deliver() will not take, so
# retrying the same stack loops forever. It is handled by returning the stack (see below).
TRANSIENT = ("busy", "output_full", "source_changed", "target_changed")


def remaining(order, fragment_id):
    # in_transit already counts samples staged in an Exchange input, including this one.
    wanted = order.requires.get(fragment_id, 0)
    return wanted - order.delivered.get(fragment_id, 0) - order.in_transit.get(fragment_id, 0)


def find_sample(exchange, order, stacks):
    """A stack in Inventory the order still needs. Only for taking, not for delivering."""
    for stack in stacks:
        if stack.count <= 0 or remaining(order, stack.id) <= 0:
            continue
        if exchange.matches_order(stack.id, stack.properties):
            return stack
    return None


def accepted_stack(exchange, stacks):
    """A staged stack the order accepts. Staged samples are already counted in in_transit, so
    remaining() can be 0 for them; they must still be delivered, not skipped."""
    for stack in stacks:
        if stack.count > 0 and exchange.matches_order(stack.id, stack.properties):
            return stack
    return None


def assign_order(exchange, orders, inventory):
    """Assign the first open order that Inventory can fill. Returns True when one is assigned."""
    for candidate in orders:
        if candidate.status == "complete":
            continue
        if not any(remaining(candidate, fragment_id) > 0 for fragment_id in candidate.requires):
            continue
        assigned = exchange.set_order(candidate.id)
        if assigned.status != "ok":
            continue
        # matches_order reads the active order, so the sample check runs after set_order.
        if find_sample(exchange, candidate, inventory.stacks()) is not None:
            return True
        exchange.clear_order()
    return False


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


def eject_stray_inputs(exchange, order_active):
    """Eject staged samples that the active order does not accept. Returns the first refusal."""
    for stack in self.input.stacks():
        if order_active and exchange.matches_order(stack.id, stack.properties):
            continue
        ejected = self.input.eject("inventory", stack.id, stack.count, stack.properties, "exact")
        if ejected.status not in ("ok", "partial", "no_op"):
            return ejected.status
    return "ok"


def blocked(message):
    print("warning: " + message)
    set_status(message, "warn")
    sleep(PAUSE_SECONDS)


def wait(message):
    set_status(message, "info")
    sleep(RETRY_SECONDS)


while True:
    inventory = get_component("inventory")
    if inventory is None:
        blocked("inventory not found: the Bio Exchange needs home base")
        continue

    if len(self.output.stacks()) > 0:
        shipped = ship_output()
        if shipped != "ok":
            blocked("output not shipped (" + shipped + ")")
        continue

    order = self.active_order()
    if order is None or order.status == "complete":
        if order is not None:
            cleared = self.clear_order()
            if cleared.status != "ok":
                wait("clear_order " + cleared.status)
            continue
        cleared = eject_stray_inputs(self, False)
        if cleared != "ok":
            wait("clearing input: " + cleared)
            continue
        if not assign_order(self, self.orders(), inventory):
            set_status("no open Bio Order that Inventory can fill", "info")
            sleep(PAUSE_SECONDS)
        continue

    stray = eject_stray_inputs(self, True)
    if stray != "ok":
        wait("clearing input: " + stray)
        continue

    if accepted_stack(self, self.input.stacks()) is not None:
        delivered = self.deliver()
        if delivered.status == "complete":
            set_status("order complete: " + order.name, "info")
        elif delivered.status == "ok":
            set_status("delivered toward " + order.name, "info")
        elif delivered.status in TRANSIENT:
            wait("deliver " + delivered.status)
        elif delivered.status == "no_input":
            # Hand the staged sample back so the input is free, and say why. The pause keeps a
            # refused sample from being restaged every few seconds.
            stuck = accepted_stack(self, self.input.stacks())
            if stuck is None:
                wait("deliver no_input")
            else:
                returned = self.input.eject(
                    "inventory", stuck.id, stuck.count, stuck.properties, "exact"
                )
                if returned.status in ("ok", "partial"):
                    blocked("deliver no_input for " + stuck.id + ": returned to Inventory")
                else:
                    blocked("deliver no_input, return failed: " + returned.status)
        else:
            blocked("deliver " + delivered.status + ": " + delivered.message)
        continue

    sample = find_sample(self, order, inventory.stacks())
    if sample is None:
        set_status("waiting for samples for " + order.name, "info")
        sleep(PAUSE_SECONDS)
        continue

    amount = min(sample.count, remaining(order, sample.id), INPUT_CAPACITY)
    linked = self.input.connect("inventory")
    if linked.status != "ok":
        blocked("input connect: " + linked.status + ": " + linked.message)
        continue
    taken = self.input.take(sample.id, amount, sample.properties, "exact")
    if taken.status in ("ok", "partial") and taken.moved > 0:
        set_status("staging " + sample.id + " for " + order.name, "info")
    elif taken.status in TRANSIENT:
        wait("take " + taken.status)
    else:
        blocked("take " + sample.id + ": " + taken.status + ": " + taken.message)
