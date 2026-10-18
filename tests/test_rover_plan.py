"""Unit tests for the rover_plan Library: tiers, contact order, target choice and energy gates."""

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


# --- energy -------------------------------------------------------------------------------------


def test_unit_mining_wh_matches_manual_example():
    # Manual: basic drill, iron, standard site: 15 min at 10 W = 2.5 Wh.
    assert rp.unit_mining_wh("drill_module", "iron_ore", "standard") == pytest.approx(2.5)


def test_unit_mining_wh_rich_site_halves_energy_per_unit():
    assert rp.unit_mining_wh("drill_module", "iron_ore", "rich") == pytest.approx(1.25)


def test_unit_mining_wh_industrial_faster_but_draws_more():
    basic = rp.unit_mining_wh("drill_module", "titanium", "standard")
    industrial = rp.unit_mining_wh("drill_module_industrial", "titanium", "standard")
    # Industrial: 20 W for 15 min (300 W-min). Basic: 10 W for 20 min (200 W-min).
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


def test_pending_contacts_drops_scanned_and_visited():
    points = [
        {"x": 1, "y": 1, "scanned": False},
        {"x": 2, "y": 2, "scanned": True},
        {"x": 3, "y": 3, "scanned": False},
    ]
    left = rp.pending_contacts(points, visited={(3, 3)})
    assert [(p["x"], p["y"]) for p in left] == [(1, 1)]


def test_pending_contacts_nearest_to_origin_first():
    points = [
        {"x": 900, "y": 0, "scanned": False},
        {"x": -30, "y": 40, "scanned": False},
        {"x": 100, "y": 0, "scanned": False},
    ]
    order = rp.pending_contacts(points, visited=set())
    assert [(p["x"], p["y"]) for p in order] == [(-30, 40), (100, 0), (900, 0)]


def test_pending_contacts_orders_from_given_origin():
    points = [{"x": 0, "y": 0, "scanned": False}, {"x": 500, "y": 0, "scanned": False}]
    order = rp.pending_contacts(points, visited=set(), origin=(500, 0))
    assert order[0]["x"] == 500


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
