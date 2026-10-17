import json

import pytest

from tools.sync_to_game import (
    Action,
    apply_actions,
    collect_repo_files,
    is_protected,
    load_state,
    plan_one,
    plan_sync,
    read_fleet_scripts,
    save_state,
    sha256,
    summarize_log,
)

# Every test uses temp folders. The real game folder is never touched.


@pytest.mark.parametrize(
    "target",
    [
        "boot.py",
        "user_stubs.py",
        "builtins.pyi",
        "__builtins__.pyi",
        "codeterraform-fleet.json",
        "CODE-TERRAFORM-IDE.txt",
        "logs/all.log",
        "lib/.codeterraform/x.py",
        ".vscode/settings.json",
    ],
)
def test_generated_and_user_files_are_protected(target):
    assert is_protected(target)


@pytest.mark.parametrize("target", ["scanner_1.py", "lib/sensors.py"])
def test_our_files_are_not_protected(target):
    assert not is_protected(target)


def test_plan_creates_when_game_has_no_file_and_we_never_wrote_it():
    assert plan_one("scanner_1.py", b"x", None, None) == Action("create", "scanner_1.py")


def test_plan_noop_when_game_already_matches_repo():
    assert plan_one("a.py", b"x", b"x", None).kind == "noop"


def test_plan_updates_when_game_unchanged_since_our_last_write():
    last = sha256(b"old")
    assert plan_one("a.py", b"new", b"old", last).kind == "update"


def test_plan_conflicts_on_unknown_game_file_with_different_content():
    action = plan_one("a.py", b"new", b"hand edit", None)
    assert action.kind == "conflict"
    assert "not written by this tool" in action.reason


def test_plan_conflicts_when_game_edited_since_our_last_write():
    last = sha256(b"old")
    assert plan_one("a.py", b"new", b"game edit", last).kind == "conflict"


def test_plan_conflicts_when_game_deleted_a_file_we_wrote():
    last = sha256(b"old")
    action = plan_one("a.py", b"new", None, last)
    assert action.kind == "conflict"
    assert "removed in game" in action.reason


def test_plan_refuses_protected_target_even_when_missing():
    assert plan_one("boot.py", b"x", None, None).kind == "refuse"


def test_plan_sync_covers_each_repo_file_in_sorted_order():
    repo = {"b.py": b"2", "a.py": b"1"}
    actions = plan_sync(repo, {"a.py": None, "b.py": None}, {})
    assert [a.target for a in actions] == ["a.py", "b.py"]
    assert all(a.kind == "create" for a in actions)


def test_collect_repo_files_maps_main_to_root_and_libs_to_lib(tmp_path):
    (tmp_path / "scripts" / "main").mkdir(parents=True)
    (tmp_path / "scripts" / "libs").mkdir(parents=True)
    (tmp_path / "scripts" / "main" / "scanner_1.py").write_bytes(b"m")
    (tmp_path / "scripts" / "libs" / "sensors.py").write_bytes(b"l")
    (tmp_path / "scripts" / "libs" / ".gitkeep").write_bytes(b"")
    files = collect_repo_files(tmp_path)
    assert files == {"scanner_1.py": b"m", "lib/sensors.py": b"l"}


def test_collect_repo_files_skips_probes(tmp_path):
    (tmp_path / "scripts" / "probes").mkdir(parents=True)
    (tmp_path / "scripts" / "probes" / "probe.py").write_bytes(b"p")
    assert collect_repo_files(tmp_path) == {}


def test_apply_writes_creates_and_updates_and_records_state(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "a.py").write_bytes(b"old")
    actions = [Action("create", "lib/sensors.py"), Action("update", "a.py")]
    repo = {"lib/sensors.py": b"lib", "a.py": b"new"}
    state = apply_actions(actions, repo, game, {"a.py": sha256(b"old")})
    assert (game / "lib" / "sensors.py").read_bytes() == b"lib"
    assert (game / "a.py").read_bytes() == b"new"
    assert state == {"lib/sensors.py": sha256(b"lib"), "a.py": sha256(b"new")}


def test_apply_never_writes_conflicts_or_refusals(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "a.py").write_bytes(b"hand edit")
    actions = [Action("conflict", "a.py"), Action("refuse", "boot.py")]
    state = apply_actions(actions, {"a.py": b"new", "boot.py": b"x"}, game, {})
    assert (game / "a.py").read_bytes() == b"hand edit"
    assert not (game / "boot.py").exists()
    assert state == {}


def test_state_round_trips_through_json(tmp_path):
    path = tmp_path / "state.json"
    save_state(path, {"a.py": "abc"})
    assert load_state(path) == {"a.py": "abc"}
    assert json.loads(path.read_text(encoding="utf-8")) == {"files": {"a.py": "abc"}}


def test_load_state_is_empty_before_first_sync(tmp_path):
    assert load_state(tmp_path / "missing.json") == {}


def test_summarize_log_keeps_only_warn_and_error_lines():
    lines = [
        "[t] [system] [boot] > ok\n",
        "[t] [warn] [boot] > low power\n",
        "[t] [error] [x] > boom\n",
        "[t] [output] [boot] > activate_power()\n",
    ]
    assert summarize_log(lines) == ["[t] [warn] [boot] > low power", "[t] [error] [x] > boom"]


def test_read_fleet_scripts_reads_scripts_section(tmp_path):
    fleet = {"scripts": {"scanner_1": {"status": "idle", "errorMessage": None}}}
    (tmp_path / "codeterraform-fleet.json").write_text(json.dumps(fleet), encoding="utf-8")
    assert read_fleet_scripts(tmp_path) == {"scanner_1": {"status": "idle", "errorMessage": None}}


def test_read_fleet_scripts_empty_when_file_missing(tmp_path):
    assert read_fleet_scripts(tmp_path) == {}
