"""Pure solver for the Beat the System contract: a move that wins against every Arbiter reply. No
game calls here.

Where it runs: Library `arbiter_solver` in game (lib/), imported by the contract script.
Inputs: a board as the nine strings from `Arbiter.board()` ("", "you", "arbiter"), row-major.
Assumptions: the Arbiter plays as the manual says. It takes its own win, else blocks ours, else
    prefers centre, then corners, then edges. Ties inside a preference class are random. The
    solver does not guess which tie the Arbiter picks: a move counts only if it wins against
    every tie, so a random Arbiter cannot break the line.
API facts relied on (docs/game/manual Arbiter, 328): Arbiter.board(), Arbiter.play(cell).
"""

LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)
CENTRE = (4,)
CORNERS = (0, 2, 6, 8)
EDGES = (1, 3, 5, 7)
EMPTY = ""
YOU = "you"
ARBITER = "arbiter"


def _check_board(board):
    if len(board) != 9 or any(cell not in (EMPTY, YOU, ARBITER) for cell in board):
        raise ValueError(f"board must be nine cells of '', 'you' or 'arbiter': {board!r}")


def winner(board, mark):
    return any(all(board[cell] == mark for cell in line) for line in LINES)


def arbiter_choices(board):
    """Every cell the Arbiter may pick next. Empty when the board is full."""
    empty = [cell for cell in range(9) if board[cell] == EMPTY]
    for cell in empty:
        if winner(_with(board, cell, ARBITER), ARBITER):
            return [cell]
    for cell in empty:
        if winner(_with(board, cell, YOU), YOU):
            return [cell]
    for group in (CENTRE, CORNERS, EDGES):
        options = [cell for cell in group if board[cell] == EMPTY]
        if options:
            return options
    return []


def _with(board, cell, mark):
    updated = list(board)
    updated[cell] = mark
    return tuple(updated)


def _wins_after_our_move(board, cell, memo):
    """True when playing `cell` wins against every Arbiter reply, however the Arbiter ties."""
    after = _with(board, cell, YOU)
    if winner(after, YOU):
        return True
    if EMPTY not in after:
        return False
    for reply in arbiter_choices(after):
        answered = _with(after, reply, ARBITER)
        if winner(answered, ARBITER) or not _forced_win(answered, memo):
            return False
    return True


def _forced_win(board, memo):
    """True when, with us to move, some move wins against every Arbiter reply."""
    if board in memo:
        return memo[board]
    result = any(
        _wins_after_our_move(board, cell, memo) for cell in range(9) if board[cell] == EMPTY
    )
    memo[board] = result
    return result


def best_move(board):
    """Return a cell that wins by force from `board`, preferring an immediate win.

    Raises ValueError when the board is malformed or no move forces a win. Against the
    manual's Arbiter the empty board is a forced win for the player who moves first, so the
    contract script never reaches that error from a fresh game.
    """
    _check_board(board)
    board = tuple(board)
    empty = [cell for cell in range(9) if board[cell] == EMPTY]
    for cell in empty:
        if winner(_with(board, cell, YOU), YOU):
            return cell
    memo = {}
    for cell in empty:
        if _wins_after_our_move(board, cell, memo):
            return cell
    raise ValueError("no move forces a win from this board")
