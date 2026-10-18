"""Unit tests for the Sealed Vault maze walk (scripts/libs/maze_solver.py)."""

import random
import sys
from pathlib import Path

import pytest

LIBS = Path(__file__).resolve().parent.parent / "scripts" / "libs"
sys.path.insert(0, str(LIBS))

from maze_solver import OFFSETS, OPPOSITE, find_exit  # noqa: E402


class FakeVault:
    """A maze of cells joined by passages, with the manual's move statuses.

    `passages` is a set of (cell, direction) pairs; each passage is listed from both ends. A
    move through a missing passage is a wall and leaves the position unchanged. Directions
    use the solver's offsets, which is all the solver needs.
    """

    def __init__(self, passages, exit_cell, start=(0, 0)):
        self.passages = set(passages)
        self.exit_cell = exit_cell
        self.position = start
        self.moves = 0

    def move(self, direction):
        self.moves += 1
        if (self.position, direction) not in self.passages:
            return "wall"
        dx, dy = OFFSETS[direction]
        self.position = (self.position[0] + dx, self.position[1] + dy)
        return "exit" if self.position == self.exit_cell else "path"


def _passages_from_edges(edges):
    passages = set()
    for cell, direction in edges:
        dx, dy = OFFSETS[direction]
        other = (cell[0] + dx, cell[1] + dy)
        passages.add((cell, direction))
        passages.add((other, OPPOSITE[direction]))
    return passages


def _random_perfect_maze(size, seed):
    """Depth-first carve of a size x size grid. A tree over every cell, so the exit is reachable."""
    rng = random.Random(seed)
    seen = {(0, 0)}
    stack = [(0, 0)]
    edges = []
    while stack:
        x, y = stack[-1]
        options = [
            ((x + dx, y + dy), direction)
            for direction, (dx, dy) in OFFSETS.items()
            if 0 <= x + dx < size and 0 <= y + dy < size and (x + dx, y + dy) not in seen
        ]
        if not options:
            stack.pop()
            continue
        nxt, direction = rng.choice(options)
        seen.add(nxt)
        edges.append(((x, y), direction))
        stack.append(nxt)
    return _passages_from_edges(edges)


def test_straight_corridor_reaches_exit_with_its_directions():
    vault = FakeVault(_passages_from_edges([((0, 0), "east"), ((1, 0), "east")]), exit_cell=(2, 0))
    assert find_exit(vault.move, max_moves=50) == ["east", "east"]
    assert vault.position == (2, 0)


def test_dead_end_is_backed_out_of_before_the_right_branch():
    # North from the start is a dead end; the only way out goes east then north.
    passages = _passages_from_edges(
        [((0, 0), "north"), ((0, 0), "east"), ((1, 0), "north"), ((1, -1), "north")]
    )
    vault = FakeVault(passages, exit_cell=(1, -2))
    path = find_exit(vault.move, max_moves=50)
    assert path == ["east", "north", "north"]
    assert vault.position == (1, -2)


@pytest.mark.parametrize("seed", range(25))
def test_walk_finds_the_exit_of_a_random_perfect_maze(seed):
    size = 6
    passages = _random_perfect_maze(size, seed)
    exit_cell = (size - 1, size - 1)
    vault = FakeVault(passages, exit_cell=exit_cell)
    path = find_exit(vault.move, max_moves=size * size * 4)
    assert vault.position == exit_cell
    assert len(path) <= size * size


def test_backtracking_stays_within_the_move_budget():
    size = 8
    vault = FakeVault(_random_perfect_maze(size, seed=7), exit_cell=(size - 1, size - 1))
    find_exit(vault.move, max_moves=size * size * 4)
    # Every step, including each step back out of a dead end, counts against the budget.
    assert vault.moves <= size * size * 4


def test_unreachable_exit_raises():
    vault = FakeVault(_passages_from_edges([((0, 0), "east")]), exit_cell=(5, 5))
    with pytest.raises(RuntimeError):
        find_exit(vault.move, max_moves=100)


def test_move_cap_stops_the_walk():
    passages = _passages_from_edges([((0, 0), "east"), ((1, 0), "east"), ((2, 0), "east")])
    vault = FakeVault(passages, exit_cell=(3, 0))
    with pytest.raises(RuntimeError):
        find_exit(vault.move, max_moves=2)


def test_unknown_status_is_rejected():
    def odd_move(direction):
        return "teleport"

    with pytest.raises(ValueError):
        find_exit(odd_move, max_moves=10)


def test_refused_step_back_is_rejected():
    # The walk steps out once; the game then refuses the step back, which must stop it.
    calls = []

    def move(direction):
        calls.append(direction)
        return "path" if len(calls) == 1 else "wall"

    with pytest.raises(RuntimeError):
        find_exit(move, max_moves=10)
