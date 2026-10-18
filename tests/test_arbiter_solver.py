"""Unit tests for the Beat the System solver (scripts/libs/arbiter_solver.py)."""

import random
import sys
from pathlib import Path

import pytest

LIBS = Path(__file__).resolve().parent.parent / "scripts" / "libs"
sys.path.insert(0, str(LIBS))

from arbiter_solver import arbiter_choices, best_move, winner  # noqa: E402

EMPTY_BOARD = [""] * 9


def _board(**cells):
    """Build a board from cell=mark keyword arguments, e.g. _board(c0="you")."""
    board = [""] * 9
    for name, mark in cells.items():
        board[int(name[1:])] = mark
    return board


def test_winner_detects_row_column_and_diagonal():
    assert winner(_board(c0="you", c1="you", c2="you"), "you")
    assert winner(_board(c1="arbiter", c4="arbiter", c7="arbiter"), "arbiter")
    assert winner(_board(c2="you", c4="you", c6="you"), "you")
    assert not winner(_board(c0="you", c1="you"), "you")


def test_arbiter_takes_its_own_win_before_blocking():
    board = _board(c0="arbiter", c1="arbiter", c3="you", c4="you")
    assert arbiter_choices(board) == [2]


def test_arbiter_blocks_an_immediate_win_of_ours():
    board = _board(c0="you", c1="you", c4="arbiter")
    assert arbiter_choices(board) == [2]


def test_arbiter_prefers_centre_on_an_empty_board():
    assert arbiter_choices(EMPTY_BOARD) == [4]


def test_arbiter_prefers_corners_once_centre_is_taken():
    board = _board(c4="you")
    assert arbiter_choices(board) == [0, 2, 6, 8]


def test_arbiter_choices_empty_on_full_board():
    assert arbiter_choices(["you", "arbiter"] * 4 + ["you"]) == []


def test_best_move_takes_an_immediate_win():
    board = _board(c0="you", c1="you", c4="arbiter", c5="arbiter")
    assert best_move(board) == 2


def test_best_move_forces_a_win_from_the_empty_board():
    # Moving first, the player has a forced win against the manual's Arbiter (checked offline).
    cell = best_move(EMPTY_BOARD)
    assert cell in range(9)


def test_best_move_rejects_malformed_board():
    with pytest.raises(ValueError):
        best_move(["", "", ""])
    with pytest.raises(ValueError):
        best_move(["maybe"] + [""] * 8)


def test_best_move_raises_when_no_move_is_left():
    with pytest.raises(ValueError):
        best_move(
            ["you", "arbiter", "you", "arbiter", "you", "arbiter", "arbiter", "you", "arbiter"]
        )


def _arbiter_reply(board, rng):
    """Pick one Arbiter move at random among its allowed ties (the manual's policy)."""
    return rng.choice(arbiter_choices(board))


@pytest.mark.parametrize("seed", range(40))
def test_forced_line_beats_every_arbiter_tie_break(seed):
    # Play a whole game with random Arbiter ties. The solver's line must end in our win.
    rng = random.Random(seed)
    board = list(EMPTY_BOARD)
    while True:
        cell = best_move(board)
        board[cell] = "you"
        if winner(board, "you"):
            break
        assert any(mark == "" for mark in board), "the line ended in a draw"
        board[_arbiter_reply(board, rng)] = "arbiter"
        assert not winner(board, "arbiter"), "the line let the Arbiter win"
