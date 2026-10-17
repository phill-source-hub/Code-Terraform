"""Adapter test: run the real Xenogenetics contract script against the fake game."""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "contracts" / "xenogenetics.py"


def _run(earth, samples):
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
    owner = SimpleNamespace(
        contract=SimpleNamespace(id="xenogenetics", earth_ref=earth, samples=samples)
    )
    run_script(
        SCRIPT.read_text(encoding="utf-8"),
        game,
        filename=str(SCRIPT),
        extra_globals={"self": owner},
    )
    return sent, game


def test_sends_only_samples_missing_from_the_reference():
    sent, _ = _run(["ACGT", "TTGA"], ["ACGT", "GGGG", "TTGA", "CCAT"])
    assert sent == [("xenogenetics", ["GGGG", "CCAT"])]


def test_keeps_duplicate_aliens_in_original_order():
    sent, _ = _run(["AAA"], ["BBB", "AAA", "CCC", "BBB"])
    assert sent == [("xenogenetics", ["BBB", "CCC", "BBB"])]


def test_sends_empty_list_when_every_sample_is_known():
    sent, _ = _run(["AAA", "BBB"], ["AAA", "BBB"])
    assert sent == [("xenogenetics", [])]


def test_prints_count_and_transmit_status():
    _, game = _run(["AAA"], ["AAA", "BBB"])
    assert game.printed == ["1 alien samples sent: correct paid\n"]


def test_contract_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
