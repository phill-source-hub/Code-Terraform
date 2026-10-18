"""Tests for probe_rover_range: the logged numbers and the abort rules, against a simulated rover.

The simulated rover moves 10 m a tick toward its target and uses `drain` Wh per metre. Game time
advances 1/60 h a tick. The probe stops by itself, so no _Stop is needed.
"""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

PROBE = Path(__file__).resolve().parent.parent / "scripts" / "probes" / "probe_rover_range.py"


def _run(*, start_wh=100.0, drain=0.05, max_ticks_guard=20000):
    game = FakeGame()
    world = {"pos": [0.0, 0.0], "target": (0.0, 0.0), "wh": start_wh, "hours": 0.0, "ticks": 0}

    def dist(x, y):
        return ((world["pos"][0] - x) ** 2 + (world["pos"][1] - y) ** 2) ** 0.5

    def sleep(seconds, /):
        world["ticks"] += 1
        if world["ticks"] > max_ticks_guard:
            raise RuntimeError("probe did not stop")
        world["hours"] += 1 / 60
        tx, ty = world["target"]
        d = dist(tx, ty)
        if d > 0:
            step = min(10.0, d)
            px, py = world["pos"]
            world["pos"] = [px + (tx - px) * step / d, py + (ty - py) * step / d]
            world["wh"] -= step * drain

    game.sleep = sleep
    game.components["clock"] = FakeComponent(
        "clock", "clock", {"elapsed_game_hours": lambda: world["hours"]}
    )

    def set_target(x, y):
        world["target"] = (x, y)
        return SimpleNamespace(status="ok", message="")

    rover = SimpleNamespace(
        nav=SimpleNamespace(
            get_position=lambda: SimpleNamespace(x=world["pos"][0], y=world["pos"][1]),
            get_distance_to=lambda x, y: dist(x, y),
            get_speed=lambda: 50.0,
            set_target=set_target,
            set_throttle=lambda p: SimpleNamespace(status="ok", message=""),
            brake=lambda: SimpleNamespace(status="ok", message=""),
        ),
        battery=SimpleNamespace(
            level=lambda: max(world["wh"], 0.0) / 100,
            wh=lambda: world["wh"],
            capacity=lambda: 100.0,
        ),
    )
    run_script(PROBE.read_text(encoding="utf-8"), game, str(PROBE), {"self": rover})
    return game, world


def test_probe_logs_six_legs_and_three_summaries_and_ends_at_base():
    game, world = _run()

    legs = [line for line in game.printed if line.startswith("leg throttle")]
    summaries = [line for line in game.printed if line.startswith("summary throttle")]
    assert len(legs) == 6
    assert len(summaries) == 3
    assert world["pos"] == [0.0, 0.0] or abs(world["pos"][0]) < 2.0
    assert game.printed[-1].startswith("end: game hours")


def test_leg_line_reports_distance_speed_and_energy_per_metre():
    game, _ = _run(drain=0.05)

    first = next(line for line in game.printed if line.startswith("leg throttle 0.3 out"))
    # 30 m out at 0.05 Wh/m is 1.5 Wh, and the drive covers the full 30 m.
    assert "30.0 m" in first
    assert "1.5" in first and "0.05" in first


def test_summary_range_follows_from_energy_per_metre():
    game, _ = _run(drain=0.05)

    summary = next(line for line in game.printed if line.startswith("summary throttle 0.5"))
    # 100 Wh at 0.05 Wh/m is 2000 m of range.
    assert "0.05 Wh/m" in summary
    assert "2000 m" in summary
    assert "EXTRAPOLATED" in summary


def test_probe_aborts_when_battery_falls_below_the_floor():
    game, _ = _run(drain=1.0)

    assert any(line.startswith("ABORT: battery below") for line in game.printed)
    assert not any(line.startswith("summary throttle") for line in game.printed)


def test_probe_refuses_to_start_when_not_parked_at_base_with_charge():
    game, world = _run(start_wh=50.0)

    assert any(line.startswith("abort: park at base") for line in game.printed)
    assert not any(line.startswith("leg throttle") for line in game.printed)
