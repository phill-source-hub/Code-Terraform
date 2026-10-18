"""Each controller runs as one file copied to every slot, so no copy can drift (ADR-034).

Adding a slot means copying the family's first file (solar_1, o2gen_1, pressure_1) to the new
name. These tests find copies by glob, so no list needs editing.
"""

import re
from pathlib import Path

import pytest

MAIN = Path(__file__).resolve().parent.parent / "scripts" / "main"
FAMILIES = ["solar", "o2gen", "pressure"]
COPIES = {family: sorted(MAIN.glob(f"{family}_*.py")) for family in FAMILIES}
ALL_COPIES = [script for family in FAMILIES for script in COPIES[family]]


@pytest.mark.parametrize("family", FAMILIES)
def test_each_family_has_at_least_one_script(family):
    assert COPIES[family], f"no scripts/main/{family}_*.py found"


@pytest.mark.parametrize("family", FAMILIES)
def test_every_copy_is_byte_identical_to_the_family_source(family):
    source = COPIES[family][0].read_bytes()
    for script in COPIES[family]:
        assert script.read_bytes() == source, script.name


@pytest.mark.parametrize("script", ALL_COPIES, ids=lambda p: p.name)
def test_copy_does_not_name_its_own_slot(script):
    # The slot is `self`; a hard-coded id would make the copies differ again.
    assert not re.search(r"(solar|o2gen|pressure)_\d", script.read_text(encoding="utf-8"))
