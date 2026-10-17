"""Adapter test: run the real Corrupted Archive contract script against a fake grid."""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "contracts" / "corrupted_archive.py"


def _run(grid):
    """grid: list of rows, each a list of words. Returns (transmitted, game)."""
    sent: list[tuple] = []
    game = FakeGame()
    game.components["transmitter"] = FakeComponent(
        id="transmitter",
        type_id="transmitter",
        methods={
            "connect": lambda planet: SimpleNamespace(status="ok", message=""),
            "transmit": lambda key, value: (
                sent.append((key, value)) or SimpleNamespace(status="correct", message="paid")
            ),
        },
    )

    def flip(row, col):
        if not (0 <= row < len(grid) and 0 <= col < len(grid[0])):
            raise ValueError("out of bounds")
        return grid[row][col]

    archive = SimpleNamespace(rows=len(grid), cols=len(grid[0]), flip=flip)
    owner = SimpleNamespace(contract=SimpleNamespace(id="corrupted_archive", archive=archive))
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    return sent, game


def test_pairs_matching_words_as_row_col_quads():
    grid = [
        ["cat", "dog"],
        ["dog", "cat"],
    ]
    sent, game = _run(grid)
    key, pairs = sent[0]
    assert key == "corrupted_archive"
    # Order is any; compare as sets of quads.
    assert sorted(pairs) == [[0, 0, 1, 1], [0, 1, 1, 0]]
    assert game.printed == ["2 pairs sent: correct paid\n"]


def test_every_cell_is_read_exactly_once_for_a_full_grid():
    grid = [["a", "b", "c", "d"], ["c", "d", "a", "b"]]
    sent, _ = _run(grid)
    pairs = sent[0][1]
    cells = sorted(tuple(pair[0:2]) for pair in pairs) + sorted(tuple(pair[2:4]) for pair in pairs)
    assert len(cells) == 8 and len(set(cells)) == 8


def test_transmits_nothing_when_a_word_has_no_partner():
    grid = [["cat", "dog"], ["dog", "fox"]]
    sent, game = _run(grid)
    assert sent == []
    assert game.printed == ["corrupted_archive failed: unmatched words 2\n"]


def test_contract_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
