"""Base watch: one Automation that reports the whole base's power and machine heartbeats.

Where it runs: an Automation (Ship Computer > Automations > + New Automation). It has no machine
    slot and no `self`, and a brownout never pauses it (manual, Automations). It replaces the
    parked power monitor (ADR-029). Sync does not copy scripts/automations/; paste into the game.
Reads: power_control.grids() (PowerGrid net, stored, capacity) and, for each machine slot in
    HEARTBEAT_SLOTS that is deployed, comms.latest_info("status.<slot>") (ADR-028).
Writes: comms.broadcast("base.alerts", [alert text]) when the alert list changes; prints each
    change; the status bar shows the current state every pass.
Rules: power_status.classify (deficit, low battery) and base_watch.heartbeat_alerts (silent or
    never-reported machines). Alerts are only shown when they change, so the log stays readable.
API facts relied on (docs/game/power.md, docs/game/signal-bus.md, docs/game/automations.md):
    get_component, power_control.grids(), comms.latest_info(), comms.broadcast(), set_status,
    print, sleep.
"""

from base_watch import heartbeat_alerts, status_text
from power_status import classify, summarize_grids

POLL_SECONDS = 5
# A heartbeat older than this is treated as a stopped machine (about a minute of game time).
STALE_SECONDS = 60
HEARTBEAT_SLOTS = ["harvester_1", "scanner_1"]
ALERT_CHANNEL = "base.alerts"

power = get_component("power_control")
comms = get_component("comms")
last_alerts = None


def heartbeat_ages(bus):
    # A slot with no deployed machine is not watched: it would only report "no heartbeat".
    ages = {}
    for slot in HEARTBEAT_SLOTS:
        if get_component(slot) is None:
            continue
        info = bus.latest_info("status." + slot)
        ages[slot] = None if info is None else info.age_seconds
    return ages


def report(alerts):
    if not alerts:
        print("base ok")
        return
    for line in alerts:
        print("warning: " + line)


while True:
    alerts = []
    if power is None:
        alerts.append("power_control not found")
    else:
        totals = summarize_grids(power.grids())
        alerts = classify(totals["net"], totals["stored"], totals["capacity"])
    if comms is not None:
        alerts = alerts + heartbeat_alerts(heartbeat_ages(comms), STALE_SECONDS)
        if alerts != last_alerts:
            comms.broadcast(ALERT_CHANNEL, alerts)
    if alerts != last_alerts:
        report(alerts)
        last_alerts = alerts
    set_status(status_text(alerts), "warn" if alerts else "info")
    sleep(POLL_SECONDS)
