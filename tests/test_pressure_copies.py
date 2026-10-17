"""The pressure_1 and pressure_2 scripts are the same program; only the slot name differs.

Each machine needs its own file in the game (ADR-014), so the copies are kept identical by test.
"""

from pathlib import Path

MAIN = Path(__file__).resolve().parent.parent / "scripts" / "main"


def test_pressure_scripts_differ_only_in_their_slot_name():
    one = (MAIN / "pressure_1.py").read_text(encoding="utf-8").replace("pressure_1", "SLOT")
    two = (MAIN / "pressure_2.py").read_text(encoding="utf-8").replace("pressure_2", "SLOT")
    assert one == two
