"""Adapter test: run the real Three Echoes script against a fake broadcast."""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "contracts" / "three_echoes.py"


def _run(broadcast):
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
    owner = SimpleNamespace(contract=SimpleNamespace(id="three_echoes", broadcast=broadcast))
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    return game, sent


def test_transmits_the_rebuilt_signal_under_the_contract_id():
    signal = "ECHO SIGNAL 42"
    broadcast = SimpleNamespace(freq_a=signal[0::3], freq_b=signal[1::3], freq_c=signal[2::3])
    _, sent = _run(broadcast)
    assert sent == [("three_echoes", signal)]


def test_a_bad_fragment_transmits_nothing():
    game, sent = _run(SimpleNamespace(freq_a="AB", freq_b=None, freq_c="C"))
    assert not sent
    assert game.printed[0].startswith("three_echoes failed:")
