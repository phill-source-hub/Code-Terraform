"""D6 Earth Orders: progress on the current contractor orders, and the next upcoming orders.

Where it runs: Control Room card, size 2x1 (1000 x 200). Paste this file as the card's script
    (Control Room > + New Card). Not synced: paste it in game, like the Automations.
Inputs: orders.list_orders() and orders.list_upcoming_orders(). Read only: scripts cannot create
    or cancel Earth Orders (manual).
Assumptions: Library `control_room` is in game lib/ (synced from scripts/libs/, owner go-ahead).
API facts relied on (VERIFIED stub): get_component("orders"), list_orders(), list_upcoming_orders();
    Order fields name, requires, shipped, reward_credits; panel.width(), height(), card, draw_text,
    progress_bar.
"""

from control_room import order_progress, order_totals, short_text

MARGIN = 16
LEFT_X = 16
RIGHT_X = 560
HEADER_Y = 40
FIRST_ROW_Y = 62
ROW_HEIGHT = 30
MAX_CURRENT = 4
MAX_UPCOMING = 3


def draw_current(y, order):
    done, needed = order_totals(order.requires, order.shipped)
    panel.draw_text(LEFT_X, y, short_text(order.name, 24), 13, "text-bright")
    fraction = order_progress(order.requires, order.shipped)
    panel.progress_bar(LEFT_X + 200, y - 5, 230, 10, fraction, "accent")
    panel.draw_text(LEFT_X + 445, y, str(done) + " / " + str(needed), 12, "text-value")


def draw_upcoming(y, order):
    panel.draw_text(RIGHT_X, y, short_text(order.name, 30), 13, "text-secondary")
    panel.draw_text(RIGHT_X + 340, y, str(order.reward_credits) + " cr", 12, "text-value")


while True:
    panel.clear()
    width = panel.width()
    height = panel.height()
    panel.card(4, 4, width - 8, height - 8, "EARTH ORDERS")
    orders = get_component("orders")
    if orders is None:
        panel.draw_text(MARGIN, FIRST_ROW_Y, "Earth Orders not available", 13, "text-muted")
    else:
        current = orders.list_orders()
        upcoming = orders.list_upcoming_orders()
        panel.draw_text(LEFT_X, HEADER_Y, "CURRENT", 11, "text-muted")
        panel.draw_text(RIGHT_X, HEADER_Y, "UPCOMING", 11, "text-muted")
        if not current:
            panel.draw_text(
                LEFT_X, FIRST_ROW_Y, "No contractor shipment right now", 13, "text-muted"
            )
        for index, order in enumerate(current[:MAX_CURRENT]):
            draw_current(FIRST_ROW_Y + index * ROW_HEIGHT, order)
        if not upcoming:
            panel.draw_text(RIGHT_X, FIRST_ROW_Y, "Nothing queued", 13, "text-muted")
        for index, order in enumerate(upcoming[:MAX_UPCOMING]):
            draw_upcoming(FIRST_ROW_Y + index * ROW_HEIGHT, order)
