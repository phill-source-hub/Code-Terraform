"""Adapter tests: the scanner_1 snake scan against a fake scanner, Data Archive and clock."""

import json
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_comms import FakeSignalBus
from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "scanner_1.py"


class _Stop(Exception):
    """Ends the scanner's endless loop."""


class StopOnSleep(FakeGame):
    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        raise _Stop


def _notebook(saves: list, stored: dict | None = None):
    values = dict(stored or {})

    def get_value(key, default=None):
        return values.get(key, default)

    def set_value(key, value):
        # The Data Archive stores a copy and requires JSON-safe values (manual: Value rules).
        copied = json.loads(json.dumps(value))
        saves.append((key, copied))
        values[key] = copied
        return SimpleNamespace(status="ok", message="")

    return FakeComponent(
        id="notebook", type_id="notebook", methods={"get": get_value, "set": set_value}
    )


def _map_saved(saves):
    return [value for key, value in saves if key == "scanner.map"][-1]


def run_grid(results=None, notebook=True, seconds=3600.0, source_override=None, stored=None):
    """Run one full pass of the scanner. Returns (scans, saves, game)."""
    results = results or {}
    scans: list[str] = []
    saves: list = []
    game = StopOnSleep()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: seconds}
    )
    if notebook:
        game.components["notebook"] = _notebook(saves, stored)

    def scan(name):
        scans.append(name)
        return results.get(name, SimpleNamespace(status="empty", message="", name=None, value=None))

    owner = SimpleNamespace(scan=scan)
    source = SCRIPT.read_text(encoding="utf-8")
    if source_override:
        source = source_override(source)
    with suppress(_Stop):
        run_script(source, game, filename=str(SCRIPT), extra_globals={"self": owner})
    return scans, saves, game


def test_first_row_runs_left_to_right_then_second_row_right_to_left():
    scans, _, _ = run_grid()
    assert scans[:3] == ["A1", "A2", "A3"]
    assert scans[23] == "A24"
    assert scans[24] == "B24"
    assert scans[25] == "B23"


def test_every_sector_is_scanned_exactly_once_in_one_pass():
    scans, _, _ = run_grid()
    assert len(scans) == 192
    assert len(set(scans)) == 192


def test_map_is_saved_once_per_complete_pass_not_per_row():
    _, saves, _ = run_grid()
    map_saves = [value for key, value in saves if key == "scanner.map"]
    assert len(map_saves) == 1
    assert len(map_saves[0]) == 192


def test_map_is_saved_before_the_pass_counter():
    # A harvester that sees the new pass number must find the map for it already written.
    _, saves, _ = run_grid()
    assert [key for key, _ in saves] == ["scanner.map", "scanner.pass"]


def test_pass_counter_continues_from_the_stored_value():
    _, saves, _ = run_grid(stored={"scanner.pass": 4})
    assert ("scanner.pass", 5) in saves


def test_a_missing_or_bad_pass_counter_starts_at_one():
    _, saves, _ = run_grid(stored={"scanner.pass": "four"})
    assert ("scanner.pass", 1) in saves


def test_map_entries_hold_status_name_and_value():
    results = {"E13": SimpleNamespace(status="ok", message="", name="Soil Sample", value=50)}
    _, saves, _ = run_grid(results=results)
    final = _map_saved(saves)
    assert final["E13"] == {"status": "ok", "name": "Soil Sample", "value": 50}
    assert final["A1"] == {"status": "empty", "name": None, "value": None}


def test_prints_found_items_only():
    results = {"C5": SimpleNamespace(status="ok", message="", name="Crystal Shard", value=200)}
    _, _, game = run_grid(results=results)
    assert game.printed == ["C5: Crystal Shard\n"]


def test_other_statuses_warn_and_the_scan_goes_on():
    results = {"A2": SimpleNamespace(status="busy", message="busy", name=None, value=None)}
    scans, _, game = run_grid(results=results)
    assert ("A2 busy", "warn") in game.statuses
    assert len(scans) == 192


def test_without_data_archive_the_scan_still_runs():
    scans, saves, game = run_grid(notebook=False)
    assert len(scans) == 192
    assert saves == []
    assert game.statuses[-1] == ("map of 192 sectors saved", "info")


def test_failed_save_is_a_warning_not_a_stop():
    game = StopOnSleep()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 3600.0}
    )
    game.components["notebook"] = FakeComponent(
        id="notebook",
        type_id="notebook",
        methods={
            "get": lambda key, default=None: default,
            "set": lambda key, value: SimpleNamespace(status="invalid_key", message="bad"),
        },
    )
    scans: list[str] = []
    owner = SimpleNamespace(
        scan=lambda name: (
            scans.append(name) or SimpleNamespace(status="empty", message="", name=None, value=None)
        )
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    assert ("map save invalid_key: bad", "warn") in game.statuses
    assert len(scans) == 192


def test_a_failed_map_save_does_not_advance_the_pass_counter():
    # The counter would tell the harvester to reset its log for a map that never arrived.
    attempts: list = []

    def refuse(key, value):
        attempts.append(key)
        return SimpleNamespace(status="invalid_key", message="bad")

    game = StopOnSleep()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 3600.0}
    )
    game.components["notebook"] = FakeComponent(
        id="notebook",
        type_id="notebook",
        methods={"get": lambda key, default=None: default, "set": refuse},
    )
    owner = SimpleNamespace(
        scan=lambda name: SimpleNamespace(status="empty", message="", name=None, value=None)
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    assert attempts == ["scanner.map"]


def test_the_archive_is_looked_up_again_each_pass():
    # Pass 1 finds no Data Archive; it unlocks before pass 2, which must then save its map.
    saves: list = []
    archive = _notebook(saves)

    class ArchiveUnlocksAfterPassOne(FakeGame):
        def __init__(self):
            super().__init__()
            self.archive_lookups = 0
            self.sleeps = 0

        def get_component(self, name, /):
            if name == "notebook":
                self.archive_lookups += 1
                return None if self.archive_lookups == 1 else archive
            return super().get_component(name)

        def sleep(self, seconds, /):
            super().sleep(seconds)
            self.sleeps += 1
            # One hour of rest is 120 heartbeat steps; the second pass starts after the 120th.
            if self.sleeps == 121:
                raise _Stop

    game = ArchiveUnlocksAfterPassOne()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 3600.0}
    )
    owner = SimpleNamespace(
        scan=lambda name: SimpleNamespace(status="empty", message="", name=None, value=None)
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    assert [key for key, _ in saves] == ["scanner.map", "scanner.pass"]
    assert ("scanner.pass", 1) in saves


def test_repeats_after_one_world_hour():
    # Stops once the rest has run its full length, which is the start of the next pass.
    class _UntilRestEnds(FakeGame):
        def sleep(self, seconds, /):
            super().sleep(seconds)
            if self.clock.now >= 720.0:
                raise _Stop

    game = _UntilRestEnds()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 720.0}
    )
    game.components["notebook"] = _notebook([])
    owner = SimpleNamespace(
        scan=lambda name: SimpleNamespace(status="empty", message="", name=None, value=None)
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    assert game.clock.now == 720.0


class _RecordingBus(FakeSignalBus):
    """Records how many archive writes had happened when the pass was announced."""

    def __init__(self, saves: list):
        super().__init__()
        self.saves = saves
        self.saves_at_announcement: int | None = None

    def broadcast(self, channel, value):
        if channel == "scan.ready":
            self.saves_at_announcement = len(self.saves)
        return super().broadcast(channel, value)


def test_a_finished_pass_is_announced_after_its_map_and_counter_are_saved():
    saves: list = []
    bus = _RecordingBus(saves)
    game = StopOnSleep()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 3600.0}
    )
    game.components["notebook"] = _notebook(saves)
    game.components["comms"] = bus.as_component()
    owner = SimpleNamespace(
        scan=lambda name: SimpleNamespace(status="empty", message="", name=None, value=None)
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    assert bus.saves_at_announcement == 2
    assert bus.latest("scan.ready") == 1
    assert bus.latest("status.scanner_1") == {"pass": 1}


def test_every_sector_posts_a_heartbeat_so_a_slow_row_is_not_seen_as_stopped():
    beats: list = []

    class _Beats(FakeSignalBus):
        def broadcast(self, channel, value):
            if channel == "status.scanner_1":
                beats.append(value)
            return super().broadcast(channel, value)

    saves: list = []
    game = StopOnSleep()
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: 3600.0}
    )
    game.components["notebook"] = _notebook(saves)
    game.components["comms"] = _Beats().as_component()
    owner = SimpleNamespace(
        scan=lambda name: SimpleNamespace(status="empty", message="", name=None, value=None)
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": owner},
        )
    assert len(beats) >= 192


def test_the_repeat_wait_is_split_into_heartbeat_steps():
    # A full hour of rest: 120 steps of 30 s, each followed by a heartbeat.
    _, _, game = run_grid(seconds=3600.0)
    assert game.clock.now == 30.0
