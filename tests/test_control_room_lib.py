"""Tests for the Control Room dashboard Library: runway, colours, progress, channels and alerts."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "libs"))

import control_room as cr  # noqa: E402


def test_runway_is_stored_energy_over_deficit():
    assert cr.runway_hours(net_w=-100.0, stored_wh=300.0) == pytest.approx(3.0)


def test_runway_counts_reserve_storage_too():
    assert cr.runway_hours(net_w=-100.0, stored_wh=50.0, reserve_wh=50.0) == pytest.approx(1.0)


def test_runway_is_infinite_when_the_grid_is_not_draining():
    assert cr.runway_hours(net_w=0.0, stored_wh=10.0) == float("inf")
    assert cr.runway_hours(net_w=25.0, stored_wh=10.0) == float("inf")


def test_runway_with_no_storage_is_zero_hours():
    assert cr.runway_hours(net_w=-50.0, stored_wh=0.0) == 0.0


@pytest.mark.parametrize(
    ("hours", "band"),
    [(0.5, "critical"), (0.99, "critical"), (1.0, "warn"), (1.99, "warn"), (2.0, "ok")],
)
def test_runway_band_edges(hours, band):
    assert cr.runway_band(hours) == band


def test_runway_band_is_ok_when_infinite():
    assert cr.runway_band(float("inf")) == "ok"


def test_fraction_is_clamped_and_zero_without_capacity():
    assert cr.fraction_of(50.0, 100.0) == 0.5
    assert cr.fraction_of(150.0, 100.0) == 1.0
    assert cr.fraction_of(-5.0, 100.0) == 0.0
    assert cr.fraction_of(5.0, 0.0) == 0.0


def test_grid_storage_fraction_pools_batteries_and_reserve():
    assert cr.grid_storage_fraction(40.0, 100.0, 10.0, 50.0) == pytest.approx(50 / 150)


@pytest.mark.parametrize(
    ("status", "color"),
    [
        ("stranded", "red"),
        ("scrambled", "red"),
        ("stalled_no_battery", "red"),
        ("stalled_no_oil", "red"),
        ("stalled_no_route", "red"),
        ("waiting_service", "amber"),
        ("waiting_oil", "amber"),
        ("waiting_bay", "amber"),
        ("holding_weather", "amber"),
        ("being_rescued", "amber"),
        ("idle", "green"),
        ("moving", "green"),
        ("traveling", "green"),
    ],
)
def test_fleet_color_for_each_status_group(status, color):
    assert cr.fleet_color(status) == color


def test_fleet_sort_puts_red_first_then_name():
    rows = [
        {"name": "b", "color": "green"},
        {"name": "z", "color": "red"},
        {"name": "a", "color": "red"},
        {"name": "c", "color": "amber"},
    ]
    ordered = sorted(rows, key=cr.fleet_sort_key)
    assert [row["name"] for row in ordered] == ["a", "z", "c", "b"]


def test_order_progress_caps_each_item_at_what_was_asked():
    requires = {"iron_ingot": 10, "water": 10}
    shipped = {"iron_ingot": 25, "water": 5}
    assert cr.order_progress(requires, shipped) == pytest.approx(0.75)


def test_order_progress_ignores_shipped_items_the_order_does_not_need():
    assert cr.order_progress({"iron_ingot": 4}, {"copper": 99}) == 0.0


def test_order_progress_with_nothing_required_is_zero():
    assert cr.order_progress({}, {"iron_ingot": 3}) == 0.0


@pytest.mark.parametrize(
    "name",
    ["ctrl.probe.echo", "ctrl.rover_1.dispatch", "a", "x" * 64, "A-B_C:d.e"],
)
def test_valid_channel_accepts_documented_characters(name):
    assert cr.valid_channel(name) is True


@pytest.mark.parametrize("name", ["", "x" * 65, "has space", "slash/no", "bad!", None, 12])
def test_valid_channel_rejects_bad_names(name):
    assert cr.valid_channel(name) is False


def test_short_text_cuts_with_a_marker():
    assert cr.short_text("abcdef", 6) == "abcdef"
    assert cr.short_text("abcdefgh", 6) == "abc..."
    assert cr.short_text(42, 5) == "42"


def test_alerts_pick_the_urgent_items_first():
    alerts = cr.alert_lines(net_w=-10.0, runway=0.5, fleet_red_count=2, o2_missing=True)

    assert alerts[0] == ("error", "Power: under 1 h of storage at current deficit")
    assert ("error", "2 vehicle or drone needs attention") in alerts
    assert ("paused", "Oxygen sensor not repaired: O2 reads unavailable") in alerts


def test_alerts_warn_under_two_hours():
    alerts = cr.alert_lines(net_w=-10.0, runway=1.5, fleet_red_count=0, o2_missing=False)

    assert alerts == [("paused", "Power: under 2 h of storage at current deficit")]


def test_alerts_say_nominal_when_nothing_is_wrong():
    alerts = cr.alert_lines(net_w=5.0, runway=float("inf"), fleet_red_count=0, o2_missing=False)

    assert alerts == [("running", "All systems nominal")]


def test_order_totals_count_delivered_and_needed_units():
    assert cr.order_totals({"iron_ingot": 10, "water": 10}, {"iron_ingot": 25, "water": 5}) == (
        15,
        20,
    )


def test_band_and_fleet_colour_maps_cover_every_value():
    assert set(cr.BAND_DOT) == set(cr.BAND_TOKEN) == {"ok", "warn", "critical"}
    assert set(cr.FLEET_DOT) == set(cr.FLEET_TOKEN) == {"green", "amber", "red"}


def test_unit_fraction_uses_oil_for_heli_and_battery_otherwise():
    assert cr.unit_fraction("heli", None, None, 5.0, 10.0) == 0.5
    assert cr.unit_fraction("electric", 30.0, 60.0, None, None) == 0.5
    assert cr.unit_fraction("", 30.0, 60.0, None, None) == 0.5


def test_unit_fraction_treats_a_missing_reading_as_empty():
    assert cr.unit_fraction("heli", None, None, None, 10.0) == 0.0
    assert cr.unit_fraction("electric", None, 60.0, None, None) == 0.0


def test_format_message_puts_id_sender_tick_and_value_on_one_line():
    line = cr.format_message(7, "rover_1", 42, "dispatch", width=50)

    assert line == "#7 rover_1 t42 dispatch"


def test_format_message_cuts_a_long_value():
    line = cr.format_message(1, "s", 0, "y" * 100, width=10)

    assert line.endswith("yyyyyyy...")
