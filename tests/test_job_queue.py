"""Unit tests for scripts/libs/job_queue.py: which pending job the harvester takes."""

from scripts.libs.job_queue import pick_job


def test_takes_the_first_job_whose_sector_is_allowed():
    pending = [(4, "E15"), (5, "E14")]
    assert pick_job(pending, ["E14", "E15"]) == 4


def test_skips_an_unallowed_job_and_takes_the_next_one():
    pending = [(4, "H24"), (5, "E14")]
    assert pick_job(pending, ["E14"]) == 5


def test_returns_none_when_no_job_is_allowed():
    assert pick_job([(4, "H24")], ["E14"]) is None


def test_returns_none_for_an_empty_queue():
    assert pick_job([], ["E14"]) is None


def test_returns_none_when_nothing_can_be_reached_this_pass():
    assert pick_job([(4, "E14")], []) is None


def test_skips_entries_that_are_not_an_id_and_sector_pair():
    pending = [None, 7, (1, 2, 3), (6, "E14")]
    assert pick_job(pending, ["E14"]) == 6


def test_a_two_character_string_is_not_read_as_a_pair():
    # "EF" unpacks as ("E", "F"); the id is not an integer, so it must not be taken.
    assert pick_job(["EF"], ["F"]) is None


def test_a_non_integer_id_is_never_taken():
    assert pick_job([("four", "E14")], ["E14"]) is None
