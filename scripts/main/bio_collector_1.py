"""Bio Collector: fetch one fragment at a time into cargo, exploring unknown fragments first.

Where it runs: machine script slot `bio_collector_1` (self = this collector).
Self-contained on purpose (ADR-014): no imports.
Policy: nearest uncataloged fragment (scan() is nearest-first). When every nearby fragment is
    cataloged, take the nearest one the active Bio Order still requires. The order is read from
    bio_exchange_1 (public read only; the Exchange is not driven from here).
Waiting: collect() is timed (about 0.1-0.3 h), so the script pauses. The loop sleeps before
    rechecking cargo, and never collects while a specimen is still in the cargo slot.
Failure: a non-ok collect status is shown as a warning and retried after PAUSE_SECONDS.
API facts relied on (docs/game/biology.md): self.scan(), self.collect(coords), self.cargo,
    FragmentLocation .coords .distance .cataloged .fragment_id, get_component, BioOrder .requires,
    set_status, sleep.
"""

PAUSE_SECONDS = 60


def pick_fragment(locations, needed_ids):
    for location in locations:
        if not location.cataloged:
            return location
    for location in locations:
        if location.fragment_id in needed_ids:
            return location
    return None


exchange = get_component("bio_exchange_1")

while True:
    if self.cargo is not None:
        sleep(PAUSE_SECONDS)
        continue
    needed_ids = []
    if exchange is not None:
        order = exchange.active_order()
        if order is not None:
            needed_ids = list(order.requires.keys())
    target = pick_fragment(self.scan(), needed_ids)
    if target is None:
        set_status("no fragment to collect", "info")
        sleep(PAUSE_SECONDS)
        continue
    result = self.collect(target.coords)
    if result.status == "ok":
        set_status("collecting " + str(target.distance) + " away", "info")
    else:
        set_status("collect " + result.status, "warn")
        sleep(PAUSE_SECONDS)
