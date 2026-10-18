"""Bio Collector: collect the fragments open Bio Orders still need, otherwise explore.

Where it runs: machine script slot `bio_collector_1` (self = this collector).
Self-contained on purpose (ADR-014): no imports.
Each pass re-reads the world and remembers nothing, so a restart or game load resumes from
    what the machines hold. One specimen at a time: nothing is collected while the cargo slot
    is occupied.
Target choice, in order:
    1. A cataloged location whose fragment still has units missing. Units missing are worked
       out per fragment for each open Bio Order in this outpost's biome:
           requires - delivered - in_transit - in Inventory - specimens already in flight
       The largest shortfall across the orders is used, so one fragment is never counted twice.
    2. Otherwise explore: the nearest unknown location, so the Bio Lab can identify it.
    3. Otherwise idle and recheck later.
Why not "first required fragment": the old script kept collecting the first required fragment
    after it was cataloged, because it never subtracted what the order already had.
Waiting: collect() is timed and pauses this script, so the loop sleeps only when idle or blocked.
Assumption (UNVERIFIED, docs/api-notes.md): another script can read bio_lab_1.specimen. If that
    read fails, the Lab chamber is not counted and the Lab may get one specimen more than needed.
API facts relied on (docs/game/biology.md): self.scan(), self.collect(coords), self.cargo,
    self.outpost.biome, FragmentLocation .coords .distance .cataloged .fragment_id,
    Specimen .coords .fragment_id, BioOrder .id .biome .status .requires .delivered .in_transit,
    bio_exchange.orders(), inventory.count(item_id), get_component, set_status, print, sleep.
"""

PAUSE_SECONDS = 60
RETRY_SECONDS = 5
EXCHANGE_ID = "bio_exchange_1"
LAB_ID = "bio_lab_1"


def open_orders(orders, biome):
    found = []
    for order in orders:
        if order.status != "complete" and order.biome == biome:
            found.append(order)
    return found


def stock_of(orders, inventory):
    """Units of each required fragment already sitting in Inventory (home base only)."""
    stock = {}
    for order in orders:
        for fragment_id in order.requires:
            if inventory is None:
                stock[fragment_id] = 0
            else:
                stock[fragment_id] = inventory.count(fragment_id)
    return stock


def units_needed(orders, in_stock, pending):
    # Largest shortfall across the open orders: a fragment needed by two orders is one unit of
    # work, not two, so the sum would overcount.
    needed = {}
    for order in orders:
        for fragment_id, wanted in order.requires.items():
            short = wanted - order.delivered.get(fragment_id, 0)
            short -= order.in_transit.get(fragment_id, 0)
            short -= in_stock.get(fragment_id, 0)
            short -= pending.get(fragment_id, 0)
            if short > needed.get(fragment_id, 0):
                needed[fragment_id] = short
    return needed


def specimen_fragment(specimen, locations):
    """Fragment id of a specimen, or None while it is unidentified.

    A collected specimen reports no fragment until analysis, so its coords are matched against
    the scan: a cataloged location at the same coords is the same fragment.
    """
    if specimen is None:
        return None
    if specimen.fragment_id is not None:
        return specimen.fragment_id
    for location in locations:
        if location.cataloged and location.coords == specimen.coords:
            return location.fragment_id
    return None


def pending_counts(specimens, locations):
    counts = {}
    for specimen in specimens:
        fragment_id = specimen_fragment(specimen, locations)
        if fragment_id is not None:
            counts[fragment_id] = counts.get(fragment_id, 0) + 1
    return counts


def lab_specimen(lab):
    """The specimen in the Bio Lab chamber, or None when it cannot be read."""
    if lab is None:
        return None
    try:
        return lab.specimen
    except Exception:
        # Boundary: an unreadable chamber must not stop collection. Only the cargo slot counts.
        return None


def pick_target(locations, needed):
    for location in locations:
        if location.cataloged and needed.get(location.fragment_id, 0) > 0:
            return location
    for location in locations:
        if not location.cataloged:
            return location
    return None


def blocked(message):
    print("warning: " + message)
    set_status(message, "warn")
    sleep(PAUSE_SECONDS)


while True:
    if self.cargo is not None:
        set_status("holding a specimen for the Bio Lab", "info")
        sleep(RETRY_SECONDS)
        continue

    locations = self.scan()
    exchange = get_component(EXCHANGE_ID)
    inventory = get_component("inventory")
    lab = get_component(LAB_ID)

    orders = []
    if exchange is not None:
        orders = open_orders(exchange.orders(), self.outpost.biome)
    needed = units_needed(
        orders,
        stock_of(orders, inventory),
        pending_counts([lab_specimen(lab)], locations),
    )

    target = pick_target(locations, needed)
    if target is None:
        set_status("no fragment to collect for the open Bio Orders", "info")
        sleep(PAUSE_SECONDS)
        continue

    result = self.collect(target.coords)
    if result.status == "ok":
        set_status("collected a specimen " + str(target.distance) + " m away", "info")
    elif result.status == "busy":
        sleep(RETRY_SECONDS)
    else:
        blocked("collect " + result.status + ": " + result.message)
