import pytest

from scripts.libs.solar_tracker import clamp_tilt, target_tilt


@pytest.mark.parametrize(
    "elevation, expected",
    [(0.0, 90.0), (30.0, 60.0), (60.0, 30.0), (90.0, 0.0), (45.0, 45.0)],
)
def test_tilt_complements_sun_elevation(elevation, expected):
    assert target_tilt(elevation) == pytest.approx(expected)


def test_night_rests_flat_up_at_ninety():
    assert target_tilt(0.0) == 90.0


@pytest.mark.parametrize("elevation, expected", [(-5.0, 90.0), (120.0, 0.0)])
def test_out_of_range_elevation_is_clamped(elevation, expected):
    assert target_tilt(elevation) == expected


@pytest.mark.parametrize("tilt, expected", [(-1.0, 0.0), (0.0, 0.0), (45.0, 45.0), (95.0, 90.0)])
def test_clamp_keeps_tilt_in_panel_range(tilt, expected):
    assert clamp_tilt(tilt) == expected
