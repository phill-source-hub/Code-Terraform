"""Tests for the fake Signal Bus: it must follow the documented behaviour, or script tests lie."""

import pytest

from tests.harness.fake_comms import FakeSignalBus


def test_send_returns_the_id_of_the_queued_message():
    bus = FakeSignalBus()
    sent = bus.send("jobs.collect", "E14")
    assert sent.status == "ok"
    assert sent.message_id == 1


def test_pending_lists_waiting_messages_oldest_first_without_taking_them():
    bus = FakeSignalBus()
    bus.send("jobs.collect", "E14")
    bus.send("jobs.collect", "E15")
    listed = bus.pending("jobs.collect")
    assert [m.value for m in listed] == ["E14", "E15"]
    assert len(bus.pending("jobs.collect")) == 2


def test_receive_with_no_id_takes_the_oldest_and_consumes_it():
    bus = FakeSignalBus()
    bus.send("jobs.collect", "E14")
    bus.send("jobs.collect", "E15")
    first = bus.receive("jobs.collect")
    assert first.status == "ok" and first.packet.value == "E14"
    assert [m.value for m in bus.pending("jobs.collect")] == ["E15"]


def test_receive_by_id_takes_exactly_that_message():
    bus = FakeSignalBus()
    bus.send("jobs.collect", "E14")
    second = bus.send("jobs.collect", "E15")
    taken = bus.receive("jobs.collect", second.message_id)
    assert taken.packet.value == "E15"
    assert [m.value for m in bus.pending("jobs.collect")] == ["E14"]


def test_a_message_can_be_received_only_once():
    bus = FakeSignalBus()
    sent = bus.send("jobs.collect", "E14")
    assert bus.receive("jobs.collect", sent.message_id).status == "ok"
    assert bus.receive("jobs.collect", sent.message_id).status == "not_found"


def test_receive_on_an_empty_channel_reports_empty():
    assert FakeSignalBus().receive("jobs.collect").status == "empty"


def test_cancel_removes_one_waiting_message():
    bus = FakeSignalBus()
    sent = bus.send("jobs.collect", "E14")
    assert bus.cancel("jobs.collect", sent.message_id).status == "ok"
    assert bus.pending("jobs.collect") == []


def test_broadcast_replaces_the_value_and_latest_reads_it_without_consuming():
    bus = FakeSignalBus()
    bus.broadcast("status.harvester_1", {"heat": 10})
    bus.broadcast("status.harvester_1", {"heat": 12})
    assert bus.latest("status.harvester_1") == {"heat": 12}
    assert bus.latest("status.harvester_1") == {"heat": 12}


def test_latest_of_a_channel_never_broadcast_is_none():
    assert FakeSignalBus().latest("scan.ready") is None


def test_a_malformed_channel_is_rejected_by_send_and_raises_on_latest():
    bus = FakeSignalBus()
    assert bus.send("bad channel!", 1).status == "invalid_channel"
    with pytest.raises(ValueError):
        bus.latest("bad channel!")


def test_as_component_exposes_the_methods_scripts_call():
    bus = FakeSignalBus()
    comms = bus.as_component()
    comms.broadcast("scan.ready", 3)
    assert comms.latest("scan.ready") == 3
