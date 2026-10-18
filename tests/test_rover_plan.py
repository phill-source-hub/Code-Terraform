"""Unit tests for the rover_plan Library: stops, tiers, target choice and energy gates."""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "libs"))

import rover_plan as rp  # noqa: E402


def site(item="iron_ore", hardness=1, purity="standard", x=100.0, y=0.0, sid="s1"):
    return {"id": sid, "x": x, "y": y, "item_id": item, "hardness": hardness, "purity": purity}


# --- module tiers -------------------------------------------------------------------------------


def test_best_drill_picks_highest_hardness_owned():
    owned = ["drill_module", "drill_module_heavy", "drill_module_industrial"]
    assert rp.best_drill(owned) == "drill_module_heavy"


def test_best_drill_ignores_non_drills_and_returns_none_when_empty():
    assert rp.best_drill(["nav_module", "sonar_module"]) is None
    assert rp.best_drill([]) is None


def test_best_sonar_picks_longest_range():
    assert rp.best_sonar(["sonar_module", "sonar_module_wide"]) == "sonar_module_wide"
    assert rp.best_sonar([]) is None


# --- survey stops -------------------------------------------------------------------------------


def test_survey_stops_cover_box_including_edges():
    stops = rp.survey_stops((0, 100, 0, 50), 50)
    xs = {x for x, _ in stops}
    ys = {y for _, y in stops}
    assert xs == {0, 50, 100}
    assert ys == {0, 50}


def test_survey_stops_alternate_direction_each_row():
    stops = rp.survey_stops((0, 20, 0, 10), 10)
    row0 = [x for x, y in stops if y == 0]
    row1 = [x for x, y in stops if y == 10]
    assert row0 == [0, 10, 20]
    assert row1 == [20, 10, 0]


def test_survey_stops_grid_point_is_within_sonar_range_of_every_map_point():
    # A stop at spacing s leaves the farthest map point s / sqrt(2) away; the spacing factor
    # keeps that under the range.
    rng = 50
    spacing = rp.STOP_SPACING_FACTOR * rng
    stops = rp.survey_stops((0, 300, 0, 300), spacing)
    worst = 0.0
    for px in range(0, 301, 5):
        for py in range(0, 301, 5):
            worst = max(worst, min(math.hypot(px - x, py - y) for x, y in stops))
    assert worst <= rng


def test_survey_stops_rejects_non_positive_spacing():
    with pytest.raises(ValueError):
        rp.survey_stops((0, 10, 0, 10), 0)


def test_survey_stops_single_point_box():
    assert rp.survey_stops((5, 5, 5, 5), 10) == [(5, 5)]


# --- energy -------------------------------------------------------------------------------------


def test_unit_mining_wh_matches_manual_example():
    # Manual: basic drill, iron, standard site: 15 min at 10 W = 2.5 Wh.
    assert rp.unit_mining_wh("drill_module", "iron_ore", "standard") == pytest.approx(2.5)


def test_unit_mining_wh_rich_site_halves_energy_per_unit():
    assert rp.unit_mining_wh("drill_module", "iron_ore", "rich") == pytest.approx(1.25)


def test_unit_mining_wh_industrial_faster_but_draws_more():
    basic = rp.unit_mining_wh("drill_module", "titanium", "standard")
    industrial = rp.unit_mining_wh("drill_module_industrial", "titanium", "standard")
    # Industrial: 20 W for 15 min (300 W·min). Basic: 10 W for 20 min (200 W·min). Faster, costlier.
    assert industrial > basic


def test_unit_mining_wh_unknown_item_uses_slowest_mineral():
    known = rp.unit_mining_wh("drill_module", "neutronium", "standard")
    unknown = rp.unit_mining_wh("drill_module", "mystery_ore", "standard")
    assert unknown == pytest.approx(known)


def test_return_reserve_includes_margin_and_buffer():
    reserve = rp.return_reserve_wh(100, 0.1)
    assert reserve == pytest.approx(10 * rp.RETURN_MARGIN + rp.RETURN_BUFFER_WH)


def test_calibrated_wh_per_m_ignores_short_legs():
    assert rp.calibrated_wh_per_m(0.05, 0.3, 5) == 0.05


def test_calibrated_wh_per_m_uses_measured_rate():
    assert rp.calibrated_wh_per_m(0.05, 2.0, 100) == pytest.approx(0.02)


def test_calibrated_wh_per_m_never_negative():
    assert rp.calibrated_wh_per_m(0.05, -1.0, 100) == 0.0


# --- target choice -----------------------------------------------------------------------------


def test_choose_target_prefers_purer_site_within_reach():
    sites = [site(purity="standard", sid="a"), site(purity="pure", sid="b", x=120)]
    pick = rp.choose_target(
        sites,
        drill_id="drill_module",
        position=(0, 0),
        home=(0, 0),
        charge_wh=100,
        wh_per_m=0.05,
        cargo_free=10,
    )
    assert pick["site"]["id"] == "b"


def test_choose_target_skips_sites_above_drill_hardness():
    sites = [site(hardness=3, sid="hard")]
    pick = rp.choose_target(
        sites,
        drill_id="drill_module",
        position=(0, 0),
        home=(0, 0),
        charge_wh=100,
        wh_per_m=0.05,
        cargo_free=10,
    )
    assert pick is None


def test_choose_target_allows_harder_site_with_upgraded_drill():
    sites = [site(item="titanium", hardness=3, sid="ti")]
    pick = rp.choose_target(
        sites,
        drill_id="drill_module_industrial",
        position=(0, 0),
        home=(0, 0),
        charge_wh=100,
        wh_per_m=0.05,
        cargo_free=10,
    )
    assert pick["site"]["id"] == "ti"


def test_choose_target_skips_unsurveyed_sites():
    sites = [site(item=None, hardness=None, purity=None)]
    assert (
        rp.choose_target(
            sites,
            drill_id="drill_module",
            position=(0, 0),
            home=(0, 0),
            charge_wh=100,
            wh_per_m=0.05,
            cargo_free=10,
        )
        is None
    )


def test_choose_target_rejects_site_beyond_charge_with_return():
    # 2000 m out at 0.05 Wh/m is 100 Wh one way: nothing left to mine or return.
    sites = [site(x=2000.0, sid="far")]
    assert (
        rp.choose_target(
            sites,
            drill_id="drill_module",
            position=(0, 0),
            home=(0, 0),
            charge_wh=100,
            wh_per_m=0.05,
            cargo_free=10,
        )
        is None
    )


def test_choose_target_limits_units_to_cargo_space():
    pick = rp.choose_target(
        [site(sid="a")],
        drill_id="drill_module",
        position=(0, 0),
        home=(0, 0),
        charge_wh=100,
        wh_per_m=0.05,
        cargo_free=3,
    )
    assert pick["units"] == 3


def test_choose_target_limits_units_to_spare_charge():
    pick = rp.choose_target(
        [site(sid="a")],
        drill_id="drill_module",
        position=(0, 0),
        home=(0, 0),
        charge_wh=25,
        wh_per_m=0.05,
        cargo_free=10,
    )
    assert pick is not None
    assert pick["units"] < 10
    assert pick["units"] >= 1


def test_choose_target_returns_none_with_no_spare_charge():
    assert (
        rp.choose_target(
            [site(sid="a")],
            drill_id="drill_module",
            position=(0, 0),
            home=(0, 0),
            charge_wh=0,
            wh_per_m=0.05,
            cargo_free=10,
        )
        is None
    )


# --- contacts, arrival and map ------------------------------------------------------------------


def test_pending_contacts_drops_scanned_and_blocked():
    points = [
        {"x": 1, "y": 1, "scanned": False},
        {"x": 2, "y": 2, "scanned": True},
        {"x": 3, "y": 3, "scanned": False},
    ]
    left = rp.pending_contacts(points, blocked={(3, 3)})
    assert [(p["x"], p["y"]) for p in left] == [(1, 1)]


def test_arrived_uses_two_metre_tolerance():
    assert rp.arrived(2.0)
    assert not rp.arrived(2.01)


def test_build_map_includes_base_and_is_plain_data():
    contacts = [{"x": 5, "y": 6, "scanned": True, "kind": "mineral"}]
    sites = [{"id": "s1", "x": 5, "y": 6}]
    result = rp.build_map((0, 10, 0, 20), contacts, sites)
    assert result["base"] == {"x": 0.0, "y": 0.0}
    assert result["bounds"] == {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 20}
    assert result["contacts"][0]["scanned"] is True
    assert result["sites"] == sites
