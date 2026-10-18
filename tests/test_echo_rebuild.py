"""Unit tests for the Three Echoes rebuild (scripts/libs/echo_rebuild.py)."""

import random
import sys
from pathlib import Path

import pytest

LIBS = Path(__file__).resolve().parent.parent / "scripts" / "libs"
sys.path.insert(0, str(LIBS))

from echo_rebuild import rebuild_signal  # noqa: E402


def _split(signal):
    """Split a signal into the three fragments exactly as the manual describes them."""
    return signal[0::3], signal[1::3], signal[2::3]


def test_rebuild_restores_a_known_signal():
    assert rebuild_signal(*_split("ABCDEFGHI")) == "ABCDEFGHI"


@pytest.mark.parametrize("length", range(1, 31))
def test_rebuild_inverts_the_split_for_every_length(length):
    rng = random.Random(length)
    signal = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ ") for _ in range(length))
    assert rebuild_signal(*_split(signal)) == signal


def test_empty_fragments_give_empty_signal():
    assert rebuild_signal("", "", "") == ""


def test_non_string_fragment_is_rejected():
    with pytest.raises(TypeError):
        rebuild_signal("AB", None, "C")
