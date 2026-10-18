"""D6 Earth Orders: progress on the current contractor orders, and the next upcoming orders.

Where it runs: Control Room card. Works at any size. At 800 px wide or more the upcoming orders
    sit in a second column; narrower cards show the next one as a footer line.
    Paste this file as the card's script (Control Room > + New Card). Not synced: paste it in game,
    like the Automations.
Inputs: orders.list_orders() and orders.list_upcoming_orders(). Read only: scripts cannot create
    or cancel Earth Orders (manual).
Assumptions: Library `control_room` is in game lib/ (synced from scripts/libs/, owner go-ahead).
API facts relied on (VERIFIED stub): get_component("orders"), list_orders(), list_upcoming_orders();
    Order fields name, requires, shipped, reward_credits; panel.width(), height(), card, draw_text,
    progress_bar.
"""

from control_room import fit_text, order_progress, order_totals, rows_for

MARGIN = 16
GAP = 24
TWO_COLUMN_MIN = 800
HEADER_Y = 40
FIRST_ROW_Y = 62
ROW_HEIGHT = 30
MAX_CURRENT = 4
MAX_UPCOMING = 3


def draw_current(x, width, y, order):
    done, needed = order_totals(order.requires, order.shipped)
    name_width = width * 42 // 100
    bar_x = x + name_width + 8
    bar_width = width * 30 // 100
    units_x = bar_x + bar_width + 10
    panel.draw_text(x, y, fit_text(order.name, name_width, 13), 13, "text-bright")
    panel.progress_bar(
        bar_x, y - 5, bar_width, 10, order_progress(order.requires, order.shipped), "accent"
    )
    panel.draw_text(units_x, y, str(done) + " / " + str(needed), 12, "text-value")


def draw_upcoming(x, width, y, order):
    reward = str(order.reward_credits) + " cr"
    name_width = width - 90
    panel.draw_text(x, y, fit_text(order.name, name_width, 13), 13, "text-secondary")
    panel.draw_text(x + width - 80, y, reward, 12, "text-value")


while True:
    panel.clear()
    width = panel.width()
    height = panel.height()
    panel.card(4, 4, width - 8, height - 8, "EARTH ORDERS")
    content = width - 2 * MARGIN
    two_columns = width >= TWO_COLUMN_MIN
    left_width = content * 58 // 100 if two_columns else content
    right_x = MARGIN + left_width + GAP
    right_width = width - MARGIN - right_x
    orders = get_component("orders")
    if orders is None:
        panel.draw_text(MARGIN, FIRST_ROW_Y, "Earth Orders not available", 13, "text-muted")
    else:
        current = orders.list_orders()
        upcoming = orders.list_upcoming_orders()
        bottom_pad = 16 if two_columns else 36
        visible = rows_for(height, FIRST_ROW_Y, ROW_HEIGHT, bottom_pad)
        panel.draw_text(MARGIN, HEADER_Y, "CURRENT", 11, "text-muted")
        if not current:
            panel.draw_text(
                MARGIN, FIRST_ROW_Y, "No contractor shipment right now", 13, "text-muted"
            )
        for index, order in enumerate(current[: min(visible, MAX_CURRENT)]):
            draw_current(MARGIN, left_width, FIRST_ROW_Y + index * ROW_HEIGHT, order)
        if two_columns:
            panel.draw_text(right_x, HEADER_Y, "UPCOMING", 11, "text-muted")
            if not upcoming:
                panel.draw_text(right_x, FIRST_ROW_Y, "Nothing queued", 13, "text-muted")
            for index, order in enumerate(upcoming[: min(visible, MAX_UPCOMING)]):
                draw_upcoming(right_x, right_width, FIRST_ROW_Y + index * ROW_HEIGHT, order)
        elif upcoming:
            next_line = "upcoming: " + str(len(upcoming)) + ", next " + upcoming[0].name
            panel.draw_text(MARGIN, height - 16, fit_text(next_line, content, 12), 12, "text-muted")
