"""Pressure generator controller: one sync per sweep, inside the window that is open now.

Where it runs: every Mk I pressure generator slot, including ones added later. The same file
    runs on each one; `self` is the generator it runs on, so the file names no slot
    (ADR-034). Copy it to add one; do not edit a copy by hand.
Self-contained on purpose (ADR-014): no imports.
Rules (manual, Pressure Generator):
    the gauge sweeps 0-100 and wraps. Each sweep has a sync window (next_window_low to
    next_window_high, both included). The first sync() in a sweep counts: a hit gives +25%
    efficiency, a miss or no sync before the wrap gives -10%. Efficiency is floored at 0.
Policy, every pass, with no sleep (the game yields during loops, so the loop runs continually):
    1. read the gauge and the window together. The window changes at each wrap, so it is never
       cached;
    2. a drop in the gauge means the sweep wrapped, so the sync for the new sweep is armed again;
    3. when the gauge is inside the window and this sweep is not yet synced, call sync() once.
Status shows gauge, window and efficiency. It is updated only when it changes.
Failure: a rejected sync is printed as a warning.
API facts relied on (manual, Pressure Generator): self.gauge(), self.next_window_low(),
    self.next_window_high(), self.sync() (.status), self.efficiency(); set_status, print.
"""

last_gauge = None
synced = False
last_status = None

while True:
    gauge = self.gauge()
    low = self.next_window_low()
    high = self.next_window_high()

    if last_gauge is not None and gauge < last_gauge:
        synced = False
    last_gauge = gauge

    if not synced and low <= gauge <= high:
        result = self.sync()
        synced = True
        print(
            "sync at gauge "
            + str(round(gauge, 2))
            + " window "
            + str(round(low, 2))
            + "-"
            + str(round(high, 2))
            + ": "
            + result.status
        )
        if result.status != "ok":
            print("warning: sync " + result.status)

    status = (
        "gauge "
        + str(round(gauge, 1))
        + " window "
        + str(round(low, 1))
        + "-"
        + str(round(high, 1))
        + " efficiency "
        + str(round(self.efficiency(), 1))
        + "%"
    )
    if status != last_status:
        set_status(status, "info")
        last_status = status
