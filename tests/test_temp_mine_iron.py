"""Tests for the temporary iron-mining script: it picks the nearest iron site, mines, and delivers.

The fake rover teleports to each target, so a drive finishes at once. The probe needs no sleep cap:
the script stops by itself after MAX_TRIPS or when no iron site is left.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "probes" / "temp_mine_iron.py"
sys.path.insert(0, str(ROOT / "scripts" / "libs"))


def _site(sid, x, y, item, hardness=1):
    return SimpleNamespace(
        id=sid,
        x=x,
        y=y,
        item_id=item,
        hardness=hardness,
        purity="standard",
        kind=lambda: "mineral",
    )


def _run(sites, *, cargo_cap=10):
    game = FakeGame()
    game.components["journal"] = FakeComponent(
        "journal", "journal", {"surveyed_sites": lambda planet: sites}
    )
    world = {"pos": (0.0, 0.0), "cargo": 0, "sends": [], "targets": []}
    stacks = {}

    def set_target(x, y):
        world["targets"].append((x, y))
        world["pos"] = (x, y)
        return SimpleNamespace(status="ok", message="")

    def mine():
        if world["cargo"] >= cargo_cap:
            return SimpleNamespace(status="no_cargo_space", message="full")
        world["cargo"] += 1
        stacks["iron_ore"] = world["cargo"]
        return SimpleNamespace(status="ok", message="")

    def send(item, count):
        world["sends"].append((item, count))
        world["cargo"] = 0
        stacks.clear()
        return SimpleNamespace(status="ok", message="", moved=count)

    rover = SimpleNamespace(
        nav=SimpleNamespace(
            get_position=lambda: SimpleNamespace(x=world["pos"][0], y=world["pos"][1]),
            get_distance_to=lambda x, y: (
                ((world["pos"][0] - x) ** 2 + (world["pos"][1] - y) ** 2) ** 0.5
            ),
            set_target=set_target,
            set_throttle=lambda p: SimpleNamespace(status="ok", message=""),
            brake=lambda: SimpleNamespace(status="ok", message=""),
        ),
        battery=SimpleNamespace(level=lambda: 1.0, wh=lambda: 100.0),
        cargo=SimpleNamespace(
            count=lambda: world["cargo"],
            stacks=lambda: [SimpleNamespace(id=k, count=v) for k, v in stacks.items()],
        ),
        drill=SimpleNamespace(mine=mine),
        output=SimpleNamespace(
            connect=lambda name: SimpleNamespace(status="ok", message=""),
            send=send,
        ),
        modules=lambda: [SimpleNamespace(index=2, type="drill_basic", module_id="drill_module")],
        is_being_rescued=lambda: False,
    )
    run_script(SCRIPT.read_text(encoding="utf-8"), game, str(SCRIPT), {"self": rover})
    return game, world


def test_mines_the_iron_site_nearest_base_not_the_nearest_site_of_another_item():
    sites = [
        _site("iron_far", 300.0, 0.0, "iron_ore"),
        _site("iron_near", 50.0, 0.0, "iron_ore"),
        _site("silicon_nearer", 10.0, 0.0, "silicon"),
    ]
    game, world = _run(sites)

    assert world["targets"][0] == (50.0, 0.0)


def test_delivers_a_full_hold_to_inventory_then_repeats_the_trip():
    sites = [_site("iron_near", 50.0, 0.0, "iron_ore")]
    game, world = _run(sites)

    assert world["sends"][0] == ("iron_ore", 10)
    assert any(line.startswith("trip 1: mined 10, delivered 10") for line in game.printed)


def test_skips_sites_harder_than_the_drill():
    sites = [_site("iron_hard", 20.0, 0.0, "iron_ore", hardness=3)]
    game, world = _run(sites)

    assert world["targets"] == []
    assert any("no surveyed iron site" in line for line in game.printed)
