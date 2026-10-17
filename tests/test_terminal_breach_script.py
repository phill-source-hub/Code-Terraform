"""Adapter test: run the real Terminal Breach contract script against a fake terminal."""

import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "contracts" / "terminal_breach.py"
LENGTH = 15
MAX_GUESSES = 1 + (LENGTH) * 4 + 1  # base guess, 4 candidates per position, final check


def _score(code, guess):
    """Standard correct/misplaced scoring; repeated digits are never over-counted."""
    correct = sum(1 for c, g in zip(code, guess, strict=True) if c == g)
    leftover_code = [c for c, g in zip(code, guess, strict=True) if c != g]
    leftover_guess = [g for c, g in zip(code, guess, strict=True) if c != g]
    misplaced = 0
    for digit in set(leftover_guess):
        misplaced += min(leftover_code.count(digit), leftover_guess.count(digit))
    return SimpleNamespace(correct=correct, misplaced=misplaced)


class FakeTerminal:
    """Validates the way the briefing describes and counts guesses."""

    def __init__(self, code):
        self.code = code
        self.length = len(code)
        self.guesses: list[list[int]] = []

    def guess(self, digits):
        if type(digits) is not list:
            raise TypeError("digits must be a list")
        if any(type(d) is not int for d in digits):
            raise TypeError("digits must be whole numbers")
        if len(digits) != self.length:
            raise ValueError("expected " + str(self.length) + " digits")
        if any(d < 1 or d > 5 for d in digits):
            raise ValueError("digits must be 1-5")
        self.guesses.append(list(digits))
        return _score(self.code, digits)


def _run(code):
    """Returns (sent, game, terminal)."""
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
    terminal = FakeTerminal(code)
    owner = SimpleNamespace(contract=SimpleNamespace(id="terminal_breach", terminal=terminal))
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    return sent, game, terminal


def test_transmits_known_code_as_list_of_ints():
    code = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 5, 5, 5, 1, 1]
    sent, game, _ = _run(code)
    assert sent == [("terminal_breach", code)]
    assert game.printed == ["correct paid\n"]


def test_solves_all_same_digit_code():
    code = [4] * LENGTH
    sent, _, _ = _run(code)
    assert sent == [("terminal_breach", code)]


@pytest.mark.parametrize("seed", range(25))
def test_solves_random_codes_within_guess_budget(seed):
    rng = random.Random(seed)
    code = [rng.randint(1, 5) for _ in range(LENGTH)]
    sent, _, terminal = _run(code)
    assert sent == [("terminal_breach", code)]
    assert len(terminal.guesses) <= MAX_GUESSES


def test_every_guess_is_a_valid_15_digit_list():
    _, _, terminal = _run([5, 3, 1, 2, 4] * 3)
    assert terminal.guesses
    for guess in terminal.guesses:
        assert len(guess) == LENGTH
        assert all(type(d) is int and 1 <= d <= 5 for d in guess)


def test_transmits_nothing_when_guess_is_rejected():
    class RejectingTerminal:
        length = LENGTH

        def guess(self, digits):
            raise ValueError("digits must be 1-5")

    game = FakeGame()
    game.components["transmitter"] = FakeComponent(
        id="transmitter",
        type_id="transmitter",
        methods={
            "connect": lambda planet: SimpleNamespace(status="ok", message=""),
            "transmit": lambda key, value: pytest.fail("must not transmit"),
        },
    )
    owner = SimpleNamespace(
        contract=SimpleNamespace(id="terminal_breach", terminal=RejectingTerminal())
    )
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    assert game.printed == ["terminal_breach failed: digits must be 1-5\n"]


def _script_globals():
    """Runs the script once against a real-looking terminal and returns its globals."""
    _, _, _ = _run([1] * LENGTH)
    game = FakeGame()
    game.components["transmitter"] = FakeComponent(
        id="transmitter",
        type_id="transmitter",
        methods={
            "connect": lambda planet: SimpleNamespace(status="ok", message=""),
            "transmit": lambda key, value: SimpleNamespace(status="correct", message=""),
        },
    )
    owner = SimpleNamespace(
        contract=SimpleNamespace(id="terminal_breach", terminal=FakeTerminal([1] * LENGTH))
    )
    return run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )


def test_solve_raises_when_feedback_is_inconsistent():
    solve = _script_globals()["solve"]
    # A counter that never changes gives no signal, so the solver must refuse to guess.
    with pytest.raises(RuntimeError, match="no digit found at position 0"):
        solve(lambda digits: 0, LENGTH, [1, 2, 3, 4, 5])


def test_solve_returns_the_code_for_a_direct_counter():
    solve = _script_globals()["solve"]
    code = [2, 2, 1, 5, 3]

    def counter(digits):
        return _score(code, digits).correct

    assert solve(counter, len(code), [1, 2, 3, 4, 5]) == code


def test_contract_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
