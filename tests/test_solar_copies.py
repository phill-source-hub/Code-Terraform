"""The solar_1 and solar_2 scripts are the same program; only the slot name differs.

Each machine needs its own file in the game (ADR-014), so the copies are kept identical by test.
"""

from pathlib import Path

MAIN = Path(__file__).resolve().parent.parent / "scripts" / "main"


def test_solar_scripts_differ_only_in_their_slot_name():
    one = (MAIN / "solar_1.py").read_text(encoding="utf-8").replace("solar_1", "SLOT")
    two = (MAIN / "solar_2.py").read_text(encoding="utf-8").replace("solar_2", "SLOT")
    assert one == two


def test_both_solar_scripts_exist():
    assert (MAIN / "solar_1.py").is_file()
    assert (MAIN / "solar_2.py").is_file()
