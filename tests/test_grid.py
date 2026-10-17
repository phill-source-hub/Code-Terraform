"""Unit tests for scripts/libs/grid.py: sector names, snake order and the route search."""

import pytest

from scripts.libs.grid import (
    COLS,
    EMPTY_STEP_HEAT,
    ITEM_STEP_HEAT,
    ROWS,
    parse_sector,
    plan_routes,
    sector_id,
    snake_order,
)


def test_sector_id_maps_zero_based_cells_to_the_manual_names():
    assert sector_id(0, 0) == "A1"
    assert sector_id(4, 12) == "E13"
    assert sector_id(ROWS - 1, COLS - 1) == "H24"


def test_parse_sector_is_the_inverse_of_sector_id():
    for row in range(ROWS):
        for col in range(COLS):
            assert parse_sector(sector_id(row, col)) == (row, col)


def test_snake_order_visits_every_sector_once_in_boustrophedon_order():
    order = [name for name, _ in snake_order()]
    assert len(order) == ROWS * COLS
    assert len(set(order)) == ROWS * COLS
    assert order[:3] == ["A1", "A2", "A3"]
    assert order[COLS : COLS + 2] == ["B24", "B23"]


def test_snake_order_flags_the_last_sector_of_each_row():
    flagged = [name for name, row_end in snake_order() if row_end]
    assert len(flagged) == ROWS
    assert flagged[0] == "A24"
    assert flagged[1] == "B1"


def test_plan_routes_start_cell_costs_nothing_and_has_no_first_step():
    best, first = plan_routes((4, 12), [])
    assert best[(4, 12)] == (0, 0)
    assert first[(4, 12)] is None


def test_entering_an_item_costs_item_heat_and_an_empty_sector_costs_empty_heat():
    best, _ = plan_routes((4, 12), ["E14"])
    assert best[(4, 13)] == (ITEM_STEP_HEAT, 1)
    assert best[(4, 14)] == (ITEM_STEP_HEAT + EMPTY_STEP_HEAT, 2)


def test_first_step_is_the_neighbour_adjacent_to_the_start():
    _, first = plan_routes((4, 12), ["E14", "E15"])
    assert first[(4, 14)] == (4, 13)


def test_equal_heat_prefers_fewer_steps():
    # Detour through an empty row costs more heat, so the direct item-only path is the best.
    best, _ = plan_routes((4, 12), ["E14", "E15"])
    assert best[(4, 14)] == (2, 2)


def test_routes_reach_every_cell():
    best, _ = plan_routes((0, 0), [])
    assert len(best) == ROWS * COLS


@pytest.mark.parametrize(
    "start,target,expected_steps",
    [((0, 0), (0, 1), 1), ((0, 0), (7, 23), 30), ((3, 3), (3, 3), 0)],
)
def test_step_count_is_manhattan_distance_on_an_empty_grid(start, target, expected_steps):
    best, _ = plan_routes(start, [])
    assert best[target][1] == expected_steps
