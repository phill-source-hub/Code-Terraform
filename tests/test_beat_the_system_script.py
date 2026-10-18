"""Adapter test: run the real Beat the System script against a fake Arbiter."""

import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "contracts" / "beat_the_system.py"
LIBS = Path(__file__).resolve().parent.parent / "scripts" / "libs"
sys.path.insert(0, str(LIBS))

from arbiter_solver import arbiter_choices, winner  # noqa: E402


class FakeArbiter:
    """The manual's Arbiter: random ties inside each preference class, streak counting.

    `forced_outcome` replaces the outcome of a finished game, to test the stop path.
    `start_busy` makes the first few new_game() calls report in_progress.
    """

    def __init__(self, target, seed, forced_outcome=None, start_busy=0):
        self.target_value = target
        self.rng = random.Random(seed)
        self.forced_outcome = forced_outcome
        self.start_busy = start_busy
        self.cells = [""] * 9
        self.state = "no_game"
        self.streak_value = 0

    def target(self):
        return self.target_value

    def streak(self):
        return self.streak_value

    def board(self):
        return list(self.cells)

    def result(self):
        return self.state

    def new_game(self):
        if self.start_busy > 0:
            self.start_busy -= 1
            return SimpleNamespace(status="in_progress", message="busy")
        self.cells = [""] * 9
        self.state = "ongoing"
        return SimpleNamespace(status="ok", message="")

    def play(self, cell):
        if self.state != "ongoing" or self.cells[cell] != "":
            return SimpleNamespace(status="occupied", message="bad move")
        self.cells[cell] = "you"
        if winner(self.cells, "you"):
            return self._finish("win")
        if "" not in self.cells:
            return self._finish("draw")
        reply = self.rng.choice(arbiter_choices(self.cells))
        self.cells[reply] = "arbiter"
        if winner(self.cells, "arbiter"):
            return self._finish("loss")
        if "" not in self.cells:
            return self._finish("draw")
        return SimpleNamespace(status="ongoing", message="")

    def _finish(self, outcome):
        self.state = outcome
        self.streak_value = self.streak_value + 1 if outcome == "win" else 0
        reported = self.forced_outcome or outcome
        return SimpleNamespace(status=reported, message="")

    def token(self):
        return "PASS-" + str(self.streak_value) if self.streak_value >= self.target_value else ""


def _run(arbiter):
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
    owner = SimpleNamespace(contract=SimpleNamespace(id="beat_the_system", arbiter=arbiter))
    game.sleep = lambda seconds: None
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    return game, sent


@pytest.mark.parametrize("seed", range(20))
def test_wins_the_target_streak_and_transmits_the_passcode(seed):
    arbiter = FakeArbiter(target=5, seed=seed)
    game, sent = _run(arbiter)
    assert arbiter.streak_value == 5
    assert sent == [("beat_the_system", "PASS-5")]
    assert "correct done\n" in game.printed


def test_waits_out_a_busy_board_before_starting():
    arbiter = FakeArbiter(target=2, seed=1, start_busy=2)
    _, sent = _run(arbiter)
    assert sent == [("beat_the_system", "PASS-2")]


def test_a_lost_game_stops_before_transmitting():
    arbiter = FakeArbiter(target=3, seed=2, forced_outcome="loss")
    game, sent = _run(arbiter)
    assert sent == []
    assert any(line.startswith("beat_the_system stopped:") for line in game.printed)


def test_an_unexpected_play_status_is_reported_without_transmitting():
    arbiter = FakeArbiter(target=3, seed=3)
    arbiter.play = lambda cell: SimpleNamespace(status="teleported", message="odd")
    game, sent = _run(arbiter)
    assert sent == []
    assert game.printed[0].startswith("beat_the_system failed:")
