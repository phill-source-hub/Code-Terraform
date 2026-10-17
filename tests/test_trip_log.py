"""Unit tests for scripts/libs/trip_log.py: the harvester's per-pass visited record."""

import pytest

from scripts.libs.trip_log import is_done, mark_done, new_log, reconcile


def test_new_log_is_empty_for_its_pass():
    assert new_log(3) == {"pass": 3, "sectors": []}


def test_reconcile_keeps_a_stored_log_from_the_same_pass():
    stored = {"pass": 3, "sectors": ["E13", "E14"]}
    assert reconcile(stored, 3) is stored


def test_reconcile_starts_fresh_when_the_pass_has_changed():
    assert reconcile({"pass": 2, "sectors": ["E13"]}, 3) == new_log(3)


@pytest.mark.parametrize("junk", [None, 0, 7, "pass", [], ["E13"], {"sectors": []}])
def test_reconcile_discards_anything_that_is_not_a_log(junk):
    assert reconcile(junk, 1) == new_log(1)


def test_reconcile_discards_a_log_whose_sectors_are_not_a_list():
    assert reconcile({"pass": 1, "sectors": "E13"}, 1) == new_log(1)


def test_mark_done_adds_a_sector_once():
    log = mark_done(new_log(1), "E13")
    assert log["sectors"] == ["E13"]
    assert mark_done(log, "E13") is log


def test_mark_done_never_changes_the_log_it_was_given():
    original = new_log(1)
    mark_done(original, "E13")
    assert original == {"pass": 1, "sectors": []}


def test_is_done_reports_only_sectors_in_this_log():
    log = mark_done(new_log(1), "E13")
    assert is_done(log, "E13")
    assert not is_done(log, "E14")
