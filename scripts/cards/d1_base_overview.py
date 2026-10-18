"""D1 base overview: power, atmosphere, fleet health and the top orders, with an alert strip.

Where it runs: Control Room card. Designed for 2x2 (1000 x 400), where it shows two columns of
    sections. Narrower or shorter cards stack the sections in priority order and drop the ones that
    do not fit (power first, then fleet, atmosphere and orders).
    Paste this file as the card's script (Control Room > + New Card). Not synced: paste it in game,
    like the Automations.
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
    fit_text,
    fleet_color,
    grid_storage_fraction,
    order_progress,
    order_totals,
    place_sections,
    runway_hours,
)

MARGIN = 16
GAP = 10
TWO_COLUMN_MIN = 800
ALERT_TOP = 44
ALERT_ROW = 20
ALERT_ROWS = 3
ORDER_ROWS = 3
POWER_H = 50
ATMOSPHERE_H = 56
FLEET_H = 36
ORDERS_H = 22 + 22 * ORDER_ROWS + 10


def read_sensor(get):
    # O2 and pressure need a repaired sensor; the game raises while it is missing.
    try:
        return get()
    except Exception:
        # Boundary: an unrepaired sensor reads as None ("unavailable"), never as 0.
        return None


def value_text(value, unit):
    if value is None:
        return "unavailable"
    return str(int(value)) + " " + unit


def runway_text(hours):
    if hours == float("inf"):
        return "storage not draining"
    return "runway " + str(int(hours * 10) / 10) + " h"


def draw_power(x, y, width, total, hours):
    fraction = grid_storage_fraction(
        total.stored, total.capacity, total.reserve_stored, total.reserve_capacity
    )
    panel.draw_text(x, y, "POWER", 11, "text-muted")
    panel.progress_bar(x, y + 12, width, 12, fraction, "accent")
    panel.draw_text(x, y + 36, "net " + str(int(total.net)) + " W", 12, "text-secondary")
    panel.draw_text(x + width // 2, y + 36, runway_text(hours), 12, "text-value")


def draw_atmosphere(x, y, width, o2, pressure, n2):
    panel.draw_text(x, y, "ATMOSPHERE", 11, "text-muted")
    panel.draw_text(x, y + 22, "O2 " + value_text(o2, "ppt"), 12, "text-value")
    panel.draw_text(x + width // 2, y + 22, "N2 " + value_text(n2, "ppt"), 12, "text-value")
    panel.draw_text(x, y + 44, "pressure " + value_text(pressure, "kPa"), 12, "text-value")


def draw_fleet(x, y, width, counts):
    summary = (
        "attention "
        + str(counts["red"])
        + "   waiting "
        + str(counts["amber"])
        + "   ok "
        + str(counts["green"])
    )
    panel.draw_text(x, y, "FLEET", 11, "text-muted")
    panel.draw_text(x, y + 22, fit_text(summary, width, 12), 12, "text-value")


def draw_orders(x, y, width, current):
    panel.draw_text(x, y, "ORDERS", 11, "text-muted")
    if not current:
        panel.draw_text(x, y + 22, "No contractor shipment right now", 12, "text-muted")
    name_width = width * 40 // 100
    bar_x = x + name_width + 8
    bar_width = width * 30 // 100
    units_x = bar_x + bar_width + 10
    for index, order in enumerate(current[:ORDER_ROWS]):
        row_y = y + 22 + index * 22
        done, needed = order_totals(order.requires, order.shipped)
        panel.draw_text(x, row_y, fit_text(order.name, name_width, 12), 12, "text-bright")
        panel.progress_bar(
            bar_x, row_y - 5, bar_width, 10, order_progress(order.requires, order.shipped), "accent"
        )
        panel.draw_text(units_x, row_y, str(done) + " / " + str(needed), 12, "text-value")


def block(height, draw, args):
    return {"height": height, "draw": draw, "args": args}


def draw_blocks(blocks, x, width, top, bottom):
    places = place_sections([item["height"] for item in blocks], top, bottom, GAP)
    # Index loop rather than zip(): the game's zip is not documented with a strict flag.
    for index in range(len(blocks)):
        if places[index] is not None:
            blocks[index]["draw"](x, places[index], width, *blocks[index]["args"])


while True:
    panel.clear()
    width = panel.width()
    height = panel.height()
    panel.card(4, 4, width - 8, height - 8, "BASE OVERVIEW")
    content = width - 2 * MARGIN

    power = get_component("power_control")
    atmosphere = get_component("atmosphere")
    fleet = get_component("fleet")
    orders = get_component("orders")

    total = None
    hours = float("inf")
    net = 0.0
    if power is not None:
        total = power.total()
        hours = runway_hours(total.net, total.stored, total.reserve_stored)
        net = total.net

    o2 = None
    pressure = None
    n2 = None
    if atmosphere is not None:
        o2 = read_sensor(atmosphere.get_o2)
        pressure = read_sensor(atmosphere.get_pressure)
        n2 = atmosphere.get_n2()

    counts = {"red": 0, "amber": 0, "green": 0}
    if fleet is not None:
        for unit in fleet.vehicles() + fleet.drones():
            counts[fleet_color(unit.status)] += 1

    current = []
    if orders is not None:
        current = orders.list_orders()

    if total is None:
        panel.draw_text(MARGIN + 20, ALERT_TOP, "No power data", 13, "text-muted")
        alert_count = 1
    else:
        alerts = alert_lines(net, hours, counts["red"], o2 is None and atmosphere is not None)
        shown = alerts[:ALERT_ROWS]
        for index, (level, text) in enumerate(shown):
            row_y = ALERT_TOP + index * ALERT_ROW
            panel.status_dot(MARGIN + 6, row_y, 5, level)
            panel.draw_text(MARGIN + 20, row_y, fit_text(text, content - 20, 13), 13, "text-bright")
        alert_count = max(len(shown), 1)
    top = ALERT_TOP + alert_count * ALERT_ROW + GAP
    bottom = height - 12

    power_block = None
    if total is not None:
        power_block = block(POWER_H, draw_power, (total, hours))
    atmosphere_block = None
    if atmosphere is not None:
        atmosphere_block = block(ATMOSPHERE_H, draw_atmosphere, (o2, pressure, n2))
    fleet_block = None
    if fleet is not None:
        fleet_block = block(FLEET_H, draw_fleet, (counts,))
    orders_block = None
    if orders is not None:
        orders_block = block(ORDERS_H, draw_orders, (current,))

    if width >= TWO_COLUMN_MIN:
        left_width = (content - 2 * GAP) // 2
        right_x = MARGIN + left_width + 2 * GAP
        right_width = content - left_width - 2 * GAP
        left = [item for item in (power_block, atmosphere_block) if item is not None]
        right = [item for item in (fleet_block, orders_block) if item is not None]
        draw_blocks(left, MARGIN, left_width, top, bottom)
        draw_blocks(right, right_x, right_width, top, bottom)
    else:
        single = [
            item
            for item in (power_block, fleet_block, atmosphere_block, orders_block)
            if item is not None
        ]
        draw_blocks(single, MARGIN, content, top, bottom)
