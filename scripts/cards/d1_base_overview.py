"""D1 base overview: power, atmosphere, fleet health and the top orders, with an alert strip.

Where it runs: Control Room card, size 2x2 (1000 x 400). Paste this file as the card's script
    (Control Room > + New Card). Not synced: paste it in game, like the Automations.
Inputs: power totals, atmosphere readings, fleet units and Earth Orders. No player input.
Assumptions: Library `control_room` is in game lib/ (synced from scripts/libs/, owner go-ahead).
    An unrepaired O2 or pressure sensor shows "unavailable"; the rest of the card still draws.
API facts relied on (VERIFIED stub): get_component("power_control").total() (PowerSummary: net,
    stored, capacity, reserve_stored, reserve_capacity); get_component("atmosphere") get_o2(),
    get_n2(), get_pressure(); get_component("fleet") vehicles(), drones(); get_component("orders")
    list_orders(); panel.width(), height(), card, draw_text, status_dot, progress_bar.
"""

from control_room import (
    alert_lines,
    fleet_color,
    grid_storage_fraction,
    order_progress,
    order_totals,
    runway_hours,
    short_text,
)

MARGIN = 16
LEFT_X = 16
RIGHT_X = 520
ALERT_ROWS = 3


def draw_alerts(alerts):
    for index, (level, text) in enumerate(alerts[:ALERT_ROWS]):
        y = 44 + index * 20
        panel.status_dot(MARGIN + 6, y, 5, level)
        panel.draw_text(MARGIN + 20, y, text, 13, "text-bright")


def runway_text(hours):
    if hours == float("inf"):
        return "storage not draining"
    return "runway " + str(int(hours * 10) / 10) + " h"


def draw_power(power):
    total = power.total()
    hours = runway_hours(total.net, total.stored, total.reserve_stored)
    fraction = grid_storage_fraction(
        total.stored, total.capacity, total.reserve_stored, total.reserve_capacity
    )
    panel.draw_text(LEFT_X, 130, "POWER", 11, "text-muted")
    panel.progress_bar(LEFT_X, 142, 440, 12, fraction, "accent")
    panel.draw_text(LEFT_X, 166, "net " + str(int(total.net)) + " W", 12, "text-secondary")
    panel.draw_text(LEFT_X + 200, 166, runway_text(hours), 12, "text-value")
    return hours


def value_text(value, unit):
    if value is None:
        return "unavailable"
    return str(int(value)) + " " + unit


def read_sensor(get):
    # O2 and pressure need a repaired sensor; the game raises while it is missing.
    try:
        return get()
    except Exception:
        # Boundary: an unrepaired sensor reads as None ("unavailable"), never as 0.
        return None


def draw_atmosphere(atmosphere):
    o2 = read_sensor(atmosphere.get_o2)
    pressure = read_sensor(atmosphere.get_pressure)
    n2 = atmosphere.get_n2()
    panel.draw_text(LEFT_X, 200, "ATMOSPHERE", 11, "text-muted")
    panel.draw_text(LEFT_X, 222, "O2 " + value_text(o2, "ppt"), 12, "text-value")
    panel.draw_text(LEFT_X + 200, 222, "N2 " + value_text(n2, "ppt"), 12, "text-value")
    panel.draw_text(LEFT_X, 244, "pressure " + value_text(pressure, "kPa"), 12, "text-value")
    return o2 is None


def draw_fleet(fleet):
    counts = {"red": 0, "amber": 0, "green": 0}
    for unit in fleet.vehicles() + fleet.drones():
        counts[fleet_color(unit.status)] += 1
    panel.draw_text(RIGHT_X, 130, "FLEET", 11, "text-muted")
    summary = (
        "attention "
        + str(counts["red"])
        + "   waiting "
        + str(counts["amber"])
        + "   ok "
        + str(counts["green"])
    )
    panel.draw_text(RIGHT_X, 152, summary, 12, "text-value")
    return counts["red"]


def draw_orders(orders):
    panel.draw_text(RIGHT_X, 200, "ORDERS", 11, "text-muted")
    current = orders.list_orders()
    if not current:
        panel.draw_text(RIGHT_X, 222, "No contractor shipment right now", 12, "text-muted")
    for index, order in enumerate(current[:ALERT_ROWS]):
        y = 222 + index * 22
        done, needed = order_totals(order.requires, order.shipped)
        panel.draw_text(RIGHT_X, y, short_text(order.name, 22), 12, "text-bright")
        fraction = order_progress(order.requires, order.shipped)
        panel.progress_bar(RIGHT_X + 200, y - 5, 200, 10, fraction, "accent")
        panel.draw_text(RIGHT_X + 412, y, str(done) + " / " + str(needed), 12, "text-value")


while True:
    panel.clear()
    width = panel.width()
    height = panel.height()
    panel.card(4, 4, width - 8, height - 8, "BASE OVERVIEW")

    power = get_component("power_control")
    atmosphere = get_component("atmosphere")
    fleet = get_component("fleet")
    orders = get_component("orders")

    net = 0.0
    hours = float("inf")
    if power is not None:
        hours = draw_power(power)
        net = power.total().net
    o2_missing = False
    if atmosphere is not None:
        o2_missing = draw_atmosphere(atmosphere)
    red_units = 0
    if fleet is not None:
        red_units = draw_fleet(fleet)
    if orders is not None:
        draw_orders(orders)

    if power is None:
        # No power reading means no basis for "all systems nominal" either.
        panel.draw_text(MARGIN + 20, 44, "No power data", 13, "text-muted")
    else:
        draw_alerts(alert_lines(net, hours, red_units, o2_missing))
