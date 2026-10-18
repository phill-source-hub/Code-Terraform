"""Adapter test: run the real Sealed Vault script against a fake vault."""

import sys
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "contracts" / "sealed_vault.py"
LIBS = Path(__file__).resolve().parent.parent / "scripts" / "libs"
sys.path.insert(0, str(LIBS))

from maze_solver import OFFSETS  # noqa: E402

SIZE = 4


class FakeVault:
    """One open route: along the top row, then down the right column to the exit."""

    def __init__(self, key="KEY-7"):
        self.size = SIZE
        self.key = key
        self.position = (0, 0)
        self.open = {(x, 0) for x in range(SIZE)} | {(SIZE - 1, y) for y in range(SIZE)}
        self.exit = (SIZE - 1, SIZE - 1)
        self.escape_status = "ok"

    def move(self, direction):
        dx, dy = OFFSETS[direction]
        target = (self.position[0] + dx, self.position[1] + dy)
        if target not in self.open:
            return SimpleNamespace(status="wall", message="")
        self.position = target
        return SimpleNamespace(status="exit" if target == self.exit else "path", message="")

    def escape(self):
        if self.position != self.exit:
            return SimpleNamespace(status="not_at_exit", message="walk to the exit first", key=None)
        if self.escape_status != "ok":
            return SimpleNamespace(status=self.escape_status, message="refused", key=None)
        return SimpleNamespace(status="ok", message="", key=self.key)


def _run(vault):
    game = FakeGame()
    sent = []
    game.components["transmitter"] = FakeComponent(
        id="transmitter",
        type_id="transmitter",
        methods={
            "connect": lambda planet: SimpleNamespace(status="ok", message=""),
            "transmit": lambda key, value: (
                sent.append((key, value)) or SimpleNamespace(status="correct", message="done")
            ),
        },
    )
    owner = SimpleNamespace(contract=SimpleNamespace(id="sealed_vault", vault=vault))
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    return game, sent


def test_walks_to_the_exit_and_transmits_the_key():
    game, sent = _run(FakeVault(key="KEY-7"))
    assert sent == [("sealed_vault", "KEY-7")]
    assert any("exit in" in line for line in game.printed)


def test_a_refused_escape_transmits_nothing():
    vault = FakeVault()
    vault.escape_status = "not_at_exit"
    game, sent = _run(vault)
    assert sent == []
    assert any(line.startswith("sealed_vault escape:") for line in game.printed)
