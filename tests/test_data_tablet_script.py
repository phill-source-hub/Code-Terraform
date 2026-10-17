"""Adapter test: run the real Data Tablet contract script against a fake 2D tablet."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "contracts" / "data_tablet.py"


def _make_probe(rows, cols, message_cells):
    """message_cells: {(row, col): char}. Distance is Manhattan to the nearest message cell."""
    calls: list[tuple[int, int]] = []

    def probe(row, col):
        if type(row) is not int or type(col) is not int:
            raise TypeError("row and col must be int")
        if not (0 <= row < rows and 0 <= col < cols):
            raise ValueError("out of bounds")
        calls.append((row, col))
        if (row, col) in message_cells:
            return SimpleNamespace(char=message_cells[(row, col)], distance=0)
        if not message_cells:
            return SimpleNamespace(char=".", distance=rows + cols)
        distance = min(abs(row - r) + abs(col - c) for r, c in message_cells)
        return SimpleNamespace(char=".", distance=distance)

    probe.calls = calls
    return probe


def _run(rows, cols, message_cells):
    """Returns (sent, game, globals, probe)."""
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
    probe = _make_probe(rows, cols, message_cells)
    tablet = SimpleNamespace(rows=rows, cols=cols, probe=probe)
    owner = SimpleNamespace(contract=SimpleNamespace(id="data_tablet", tablet=tablet))
    namespace = run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    return sent, game, namespace, probe


def test_transmits_message_read_left_to_right_top_to_bottom():
    # Placed out of reading order on purpose: row 0 col 1, row 0 col 5, row 2 col 0.
    cells = {(2, 0): "C", (0, 5): "A", (0, 1): "B"}
    sent, game, _, _ = _run(3, 6, cells)
    assert sent == [("data_tablet", "BAC")]
    assert game.printed == ["3 chars sent: correct paid\n"]


def test_probes_every_cell_exactly_once():
    _, _, _, probe = _run(4, 5, {(1, 1): "X"})
    assert len(probe.calls) == 20
    assert len(set(probe.calls)) == 20


def test_reads_full_30_by_30_grid_in_row_major_order():
    cells = {(29, 29): "Z", (0, 0): "A", (15, 3): "M"}
    sent, _, _, probe = _run(30, 30, cells)
    assert sent == [("data_tablet", "AMZ")]
    assert len(probe.calls) == 900
    assert probe.calls[0] == (0, 0) and probe.calls[-1] == (29, 29)


def test_transmits_nothing_when_no_message_cells():
    sent, game, _, _ = _run(3, 3, {})
    assert sent == []
    assert game.printed == ["data_tablet failed: no message cells found\n"]


def test_transmits_nothing_when_probe_rejects_coordinates():
    rows = cols = 2

    def bad_probe(row, col):
        raise ValueError("out of bounds")

    game = FakeGame()
    game.components["transmitter"] = FakeComponent(
        id="transmitter",
        type_id="transmitter",
        methods={
            "connect": lambda planet: SimpleNamespace(status="ok", message=""),
            "transmit": lambda key, value: pytest.fail("must not transmit"),
        },
    )
    tablet = SimpleNamespace(rows=rows, cols=cols, probe=bad_probe)
    owner = SimpleNamespace(contract=SimpleNamespace(id="data_tablet", tablet=tablet))
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    assert game.printed == ["data_tablet failed: out of bounds\n"]


def test_read_message_returns_empty_string_without_message_cells():
    _, _, namespace, _ = _run(2, 2, {})
    assert namespace["read_message"](_make_probe(2, 2, {}), 2, 2) == ""


def test_read_message_collects_only_distance_zero_cells():
    namespace = _run(2, 3, {(0, 0): "H", (1, 2): "I"})[2]
    probe = _make_probe(2, 3, {(0, 0): "H", (1, 2): "I"})
    assert namespace["read_message"](probe, 2, 3) == "HI"


def test_contract_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
