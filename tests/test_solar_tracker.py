import pytest

from scripts.libs.solar_tracker import REST_TILT, choose_tilt, clamp_tilt, scan


def peaked(peak: float):
    """Output that is highest at `peak` degrees and falls off either side."""
    calls: list[float] = []

    def sample(tilt: float) -> float:
        calls.append(tilt)
        return 1000.0 - abs(tilt - peak) * 10.0

    return sample, calls


@pytest.mark.parametrize("tilt, expected", [(-5, 0.0), (0, 0.0), (45, 45.0), (95, 90.0)])
def test_clamp_keeps_tilt_in_panel_range(tilt, expected):
    assert clamp_tilt(tilt) == expected


def test_scan_finds_peak_on_its_grid():
    sample, _ = peaked(40.0)
    assert scan(sample, 0.0, 90.0, 5.0) == (40.0, 1000.0)


def test_choose_tilt_refines_to_the_one_degree_peak():
    sample, _ = peaked(37.0)
    assert choose_tilt(sample) == 37.0


def test_choose_tilt_finds_peak_at_the_edges():
    sample, _ = peaked(0.0)
    assert choose_tilt(sample) == 0.0
    sample, _ = peaked(90.0)
    assert choose_tilt(sample) == 90.0


def test_night_returns_rest_tilt():
    assert choose_tilt(lambda tilt: 0.0) == REST_TILT


def test_ties_keep_the_first_tilt():
    assert scan(lambda tilt: 5.0, 0.0, 10.0, 5.0) == (0.0, 5.0)


def test_search_uses_a_bounded_number_of_samples():
    sample, calls = peaked(63.0)
    choose_tilt(sample)
    assert len(calls) <= 30
    assert all(0.0 <= tilt <= 90.0 for tilt in calls)
