"""Every solar slot runs the same file, so there is no per-slot copy to drift (ADR-033).

Adding a generator means copying scripts/main/solar_1.py to solar_<n>.py. These tests pick up
new copies by glob, so no list needs editing.
"""

import re
from pathlib import Path

import pytest

MAIN = Path(__file__).resolve().parent.parent / "scripts" / "main"
SOLAR_SCRIPTS = sorted(MAIN.glob("solar_*.py"))


def test_there_is_at_least_one_solar_script():
    assert SOLAR_SCRIPTS, "no scripts/main/solar_*.py found"


@pytest.mark.parametrize("script", SOLAR_SCRIPTS, ids=lambda p: p.name)
def test_every_solar_script_is_byte_identical_to_the_first(script):
    assert script.read_bytes() == SOLAR_SCRIPTS[0].read_bytes()


@pytest.mark.parametrize("script", SOLAR_SCRIPTS, ids=lambda p: p.name)
def test_solar_script_does_not_name_its_own_slot(script):
    # The slot is `self`; a hard-coded id would make the copies differ again.
    assert not re.search(r"solar_\d", script.read_text(encoding="utf-8"))
