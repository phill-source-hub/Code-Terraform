"""Unit tests for scripts/libs/pacing.py: splitting a rest into heartbeat steps."""

import pytest

from scripts.libs.pacing import HEARTBEAT_STEP_SECONDS, split_sleep


def test_a_rest_shorter_than_one_step_is_one_sleep():
    assert split_sleep(12, 30) == [12]


def test_a_rest_of_exactly_one_step_is_one_sleep():
    assert split_sleep(30, 30) == [30]


def test_an_hour_splits_into_steps_of_the_heartbeat_length():
    parts = split_sleep(3600, 30)
    assert len(parts) == 120
    assert all(part == 30 for part in parts)


def test_a_remainder_is_the_last_step():
    assert split_sleep(70, 30) == [30, 30, 10]


@pytest.mark.parametrize("total", [1, 29, 31, 59.5, 3600, 720.25])
def test_the_steps_add_up_to_the_requested_rest(total):
    assert sum(split_sleep(total, 30)) == pytest.approx(total)


@pytest.mark.parametrize("total", [0, -5])
def test_no_rest_gives_no_steps(total):
    assert split_sleep(total, 30) == []


def test_every_step_is_at_most_the_step_length():
    assert max(split_sleep(3600, 30)) <= 30


def test_the_default_step_is_thirty_seconds():
    assert HEARTBEAT_STEP_SECONDS == 30
