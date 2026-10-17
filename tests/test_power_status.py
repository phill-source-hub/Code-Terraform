from types import SimpleNamespace

import pytest

from scripts.libs.power_status import (
    LOW_STORAGE_FRACTION,
    classify,
    stored_fraction,
    summarize_grids,
)


@pytest.mark.parametrize(
    ("stored", "capacity", "expected"),
    [(50, 100, 0.5), (0, 100, 0.0), (150, 100, 1.0), (-5, 100, 0.0), (10, 0, 0.0), (10, -1, 0.0)],
)
def test_stored_fraction_clamps_and_handles_no_capacity(stored, capacity, expected):
    assert stored_fraction(stored, capacity) == pytest.approx(expected)


def test_summarize_grids_sums_each_field():
    grids = [
        SimpleNamespace(net=10.0, stored=5.0, capacity=20.0),
        SimpleNamespace(net=-4.0, stored=1.0, capacity=0.0),
    ]
    assert summarize_grids(grids) == {"grids": 2.0, "net": 6.0, "stored": 6.0, "capacity": 20.0}


def test_summarize_grids_empty_list_is_all_zero():
    assert summarize_grids([]) == {"grids": 0.0, "net": 0.0, "stored": 0.0, "capacity": 0.0}


def test_classify_is_quiet_when_surplus_and_storage_healthy():
    assert classify(net_w=20.0, stored_wh=400.0, capacity_wh=500.0) == []


def test_classify_warns_on_deficit():
    assert classify(net_w=-12.4, stored_wh=400.0, capacity_wh=500.0) == ["power deficit: net -12 W"]


def test_classify_warns_on_low_storage_below_threshold():
    alerts = classify(net_w=5.0, stored_wh=LOW_STORAGE_FRACTION * 500 - 1, capacity_wh=500.0)
    assert alerts == ["low battery: 20% stored"]


def test_classify_no_low_storage_warning_without_batteries():
    assert classify(net_w=5.0, stored_wh=0.0, capacity_wh=0.0) == []


def test_classify_reports_both_problems_together():
    alerts = classify(net_w=-1.0, stored_wh=10.0, capacity_wh=500.0)
    assert len(alerts) == 2
