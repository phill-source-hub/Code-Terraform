"""D3 fleet board: one row per vehicle and drone, with a status dot, the status and a fill bar.

Where it runs: Control Room card. Works at any size; a 1x1 card shows the first few units.
    Paste this file as the card's script (Control Room > + New Card). Not synced: paste it in game,
    like the Automations.
Inputs: fleet.vehicles() and fleet.drones(). No player input.
Assumptions: Library `control_room` is in game lib/ (synced from scripts/libs/, owner go-ahead).
    Problem units (red) sort to the top, so a stranded rover is never off screen.
API facts relied on (VERIFIED stub): get_component("fleet"), vehicles(), drones(); VehicleRef and
    DroneRef fields name, status, battery_wh, battery_capacity, engine, oil_tons, oil_capacity;
    panel.width(), height(), card, draw_text, status_dot, progress_bar.
"""

from control_room import (
    FLEET_DOT,
    FLEET_TOKEN,
    fit_text,
    fleet_color,
    fleet_sort_key,
    rows_for,
    unit_fraction,
)

MARGIN = 16
FIRST_ROW_Y = 50
ROW_HEIGHT = 22
BOTTOM_PAD = 20


def vehicle_row(vehicle):
    return {
        "name": vehicle.name,
        "status": vehicle.status,
        "color": fleet_color(vehicle.status),
        "fraction": unit_fraction("", vehicle.battery_wh, vehicle.battery_capacity, None, None),
    }


def drone_row(drone):
    return {
        "name": drone.name,
        "status": drone.status,
        "color": fleet_color(drone.status),
        "fraction": unit_fraction(
            drone.engine,
            drone.battery_wh,
            drone.battery_capacity,
            drone.oil_tons,
            drone.oil_capacity,
        ),
    }


def fleet_rows(fleet):
    rows = [vehicle_row(vehicle) for vehicle in fleet.vehicles()]
    rows += [drone_row(drone) for drone in fleet.drones()]
    return sorted(rows, key=fleet_sort_key)


def draw_row(y, row, width):
    # Columns are shares of the card width, so the bar always ends inside the card.
    content = width - 2 * MARGIN
    name_x = MARGIN + 14
    status_x = MARGIN + content * 36 // 100
    bar_x = MARGIN + content * 66 // 100
    name_width = status_x - name_x - 8
    status_width = bar_x - status_x - 8
    bar_width = width - MARGIN - bar_x
    panel.status_dot(MARGIN + 6, y, 5, FLEET_DOT[row["color"]])
    panel.draw_text(name_x, y, fit_text(row["name"], name_width, 13), 13, "text-bright")
    panel.draw_text(status_x, y, fit_text(row["status"], status_width, 12), 12, "text-secondary")
    panel.progress_bar(bar_x, y - 5, bar_width, 10, row["fraction"], FLEET_TOKEN[row["color"]])


while True:
    panel.clear()
    width = panel.width()
    height = panel.height()
    panel.card(4, 4, width - 8, height - 8, "FLEET")
    fleet = get_component("fleet")
    if fleet is None:
        panel.draw_text(MARGIN, FIRST_ROW_Y, "Fleet not available", 13, "text-muted")
    else:
        rows = fleet_rows(fleet)
        if not rows:
            panel.draw_text(MARGIN, FIRST_ROW_Y, "No vehicles or drones yet", 13, "text-muted")
        visible = rows_for(height, FIRST_ROW_Y, ROW_HEIGHT, BOTTOM_PAD)
        for index, row in enumerate(rows[:visible]):
            draw_row(FIRST_ROW_Y + index * ROW_HEIGHT, row, width)
        hidden = len(rows) - visible
        if hidden > 0:
            panel.draw_text(MARGIN, height - 16, "+" + str(hidden) + " more", 11, "text-muted")
