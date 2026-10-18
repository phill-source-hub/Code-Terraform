"""D2 power runway: one gauge per power grid, with the game hours of storage left at the deficit.

Where it runs: Control Room card, size 2x1 (1000 x 200). Paste this file as the card's script
    (Control Room > + New Card). Not synced: paste it in game, like the Automations.
Inputs: power_control.grids(). No player input.
Assumptions: Library `control_room` is in game lib/ (synced from scripts/libs/, owner go-ahead).
API facts relied on (VERIFIED stub): get_component("power_control"), grids(), PowerGrid fields
    anchor_id, net, stored, capacity, reserve_stored, reserve_capacity; panel.width(), height(),
    card, draw_text, status_dot, progress_bar.
"""

from control_room import (
    BAND_DOT,
    BAND_TOKEN,
    grid_storage_fraction,
    runway_band,
    runway_hours,
    short_text,
)

MARGIN = 16
COLUMN_WIDTH = 240
MAX_COLUMNS = 4


def runway_label(hours):
    if hours == float("inf"):
        return "not draining"
    # Tenths of an hour are enough to read a gauge; int() keeps the text short.
    return "runway " + str(int(hours * 10) / 10) + " h"


def draw_grid(x, grid):
    hours = runway_hours(grid.net, grid.stored, grid.reserve_stored)
    band = runway_band(hours)
    fraction = grid_storage_fraction(
        grid.stored, grid.capacity, grid.reserve_stored, grid.reserve_capacity
    )
    panel.status_dot(x + 6, 44, 5, BAND_DOT[band])
    panel.draw_text(x + 18, 44, short_text(grid.anchor_id, 18), 13, "text-bright")
    panel.progress_bar(x, 64, 220, 12, fraction, BAND_TOKEN[band])
    panel.draw_text(x, 96, "net " + str(int(grid.net)) + " W", 12, "text-secondary")
    panel.draw_text(x, 118, runway_label(hours), 12, "text-value")


while True:
    panel.clear()
    width = panel.width()
    height = panel.height()
    panel.card(4, 4, width - 8, height - 8, "POWER RUNWAY")
    power = get_component("power_control")
    if power is None:
        panel.draw_text(MARGIN, 60, "Power control not available", 13, "text-muted")
    else:
        grids = power.grids()
        if not grids:
            panel.draw_text(MARGIN, 60, "No power grids", 13, "text-muted")
        for index, grid in enumerate(grids[:MAX_COLUMNS]):
            draw_grid(MARGIN + index * COLUMN_WIDTH, grid)
        if len(grids) > MAX_COLUMNS:
            hidden = str(len(grids) - MAX_COLUMNS)
            panel.draw_text(MARGIN, height - 20, hidden + " more grids not shown", 11, "text-muted")
