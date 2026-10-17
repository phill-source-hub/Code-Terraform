"""Unit tests for scripts/libs/base_watch.py: heartbeat staleness and the status line."""

from scripts.libs.base_watch import heartbeat_alerts, status_text


def test_fresh_heartbeats_give_no_alerts():
    assert heartbeat_alerts({"harvester_1": 5.0, "scanner_1": 30.0}, 60) == []


def test_a_heartbeat_older_than_the_limit_is_reported_with_its_age():
    assert heartbeat_alerts({"harvester_1": 120.4}, 60) == ["harvester_1: silent for 120 s"]


def test_an_age_exactly_at_the_limit_is_not_stale():
    assert heartbeat_alerts({"scanner_1": 60.0}, 60) == []


def test_a_machine_that_never_reported_is_reported_as_no_heartbeat_yet():
    assert heartbeat_alerts({"scanner_1": None}, 60) == ["scanner_1: no heartbeat yet"]


def test_alerts_are_listed_in_name_order_whatever_the_input_order():
    ages = {"scanner_1": None, "harvester_1": 999.0}
    assert heartbeat_alerts(ages, 60) == [
        "harvester_1: silent for 999 s",
        "scanner_1: no heartbeat yet",
    ]


def test_no_machines_means_no_heartbeat_alerts():
    assert heartbeat_alerts({}, 60) == []


def test_status_text_says_base_ok_when_there_are_no_alerts():
    assert status_text([]) == "base ok"


def test_status_text_counts_alerts_and_shows_the_first():
    assert status_text(["power deficit: net -5 W", "x: no heartbeat yet"]) == (
        "2 alert(s): power deficit: net -5 W"
    )
