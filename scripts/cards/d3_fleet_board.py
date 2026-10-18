"""D3 fleet board: one row per vehicle and drone, with a status dot, the status and a fill bar.

Where it runs: Control Room card, size 2x1 (1000 x 200). Paste this file as the card's script
    (Control Room > + New Card). Not synced: paste it in game, like the Automations.
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
    fleet_color,
    fleet_sort_key,
    short_text,
    unit_fraction,
)

MARGIN = 16
FIRST_ROW_Y = 50
ROW_HEIGHT = 22
NAME_X = 30
STATUS_X = 200
BAR_X = 420
BAR_WIDTH = 160


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


def draw_row(y, row):
    panel.status_dot(MARGIN + 6, y, 5, FLEET_DOT[row["color"]])
    panel.draw_text(NAME_X, y, short_text(row["name"], 20), 13, "text-bright")
    panel.draw_text(STATUS_X, y, row["status"], 12, "text-secondary")
    panel.progress_bar(BAR_X, y - 5, BAR_WIDTH, 10, row["fraction"], FLEET_TOKEN[row["color"]])


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
        visible = max((height - FIRST_ROW_Y - 20) // ROW_HEIGHT, 1)
        for index, row in enumerate(rows[:visible]):
            draw_row(FIRST_ROW_Y + index * ROW_HEIGHT, row)
        if len(rows) > visible:
            hidden = str(len(rows) - visible)
            panel.draw_text(MARGIN, height - 16, "+" + hidden + " more", 11, "text-muted")
