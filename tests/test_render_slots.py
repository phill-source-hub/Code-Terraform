"""Tests for tools/render_slots.py: one template per controller, generated files must match it."""

import pytest

from tools import render_slots
from tools.render_slots import SLOTS, TOKEN, drifted, expected_files, render


def test_render_puts_the_slot_name_wherever_the_token_is():
    assert render("slot `__SLOT__` runs __SLOT__", "solar_2") == "slot `solar_2` runs solar_2"


def test_render_leaves_text_without_the_token_unchanged():
    assert render("print('hi')\n", "solar_1") == "print('hi')\n"


def test_slot_names_with_digits_in_the_type_are_accepted():
    assert render("__SLOT__", "o2gen_3") == "o2gen_3"


@pytest.mark.parametrize("bad", ["", "solar", "Solar_1", "solar-1", "../solar_1", "solar_1 x"])
def test_render_refuses_a_name_that_is_not_a_slot_id(bad):
    with pytest.raises(ValueError):
        render("x", bad)


def test_every_slot_names_an_existing_template():
    for template in set(SLOTS.values()):
        assert (render_slots.TEMPLATES / template).is_file(), template


def test_every_template_carries_the_token():
    for template in set(SLOTS.values()):
        text = (render_slots.TEMPLATES / template).read_text(encoding="utf-8")
        assert TOKEN in text, template


def test_every_generated_file_is_the_template_rendered_for_its_slot():
    # Drift check: a hand edit to scripts/main/<slot>.py fails here. Edit the template, then run
    # `python tools/render_slots.py`.
    assert drifted(expected_files()) == []


def test_each_generated_file_names_only_its_own_slot():
    for slot in SLOTS:
        text = (render_slots.MAIN / f"{slot}.py").read_text(encoding="utf-8")
        others = [other for other in SLOTS if other != slot and other in text]
        assert others == [], f"{slot} mentions {others}"


def test_check_mode_reports_drift_and_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(render_slots, "MAIN", tmp_path)
    assert render_slots.main(["--check"]) == 1


def test_drifted_reports_a_missing_file(tmp_path):
    wanted = {tmp_path / "solar_1.py": "text"}
    assert drifted(wanted) == [tmp_path / "solar_1.py"]
