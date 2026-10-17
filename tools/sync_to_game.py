"""Sync repo scripts into the game's scripts folder, and read game status.

Where it runs: on the dev machine, outside the game. Never runs game code.
Inputs: repo `scripts/main/*.py` (game root) and `scripts/libs/*.py` (game `lib/`).
Writes: only the `apply` command, and only files we own. Generated and user files are refused.

Conflict rule: the game edits its own files (in-game edits are written back to disk). A game
file that differs from what we last wrote is a conflict and is never overwritten. State lives
in `.sync-state.json` in the repo root, which records the sha256 of each file we last wrote.

A game file whose only content is "Help me" on line 1 is an owner request to replace it
(see docs/game/external-editor.md). Any other owner code is a normal conflict.

Commands:
    plan    dry run, print what apply would do (default). --only NAME limits to one script
    apply   write the planned changes; refuses when any conflict exists unless --skip-conflicts
    pull    copy game-side edits into .sync-pull/ for review. Never touches repo files
    status  read-only: warn/error lines from logs/all.log and script status from the fleet file
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / ".sync-state.json"
# Repo folder -> prefix in the game folder. Machine and contract scripts sit at the root;
# Libraries go in lib/.
SOURCE_DIRS = {"scripts/main": "", "scripts/contracts": "", "scripts/libs": "lib/"}
PULL_DIR = REPO_ROOT / ".sync-pull"
HELP_MARKER = "Help me"
SAVE_FOLDER = "save_mvcjaxut_26ndfi_scripts"
DEFAULT_GAME_DIR = Path(os.environ.get("APPDATA", "")) / "io.codeterraform.game" / SAVE_FOLDER

# The game writes these, or the user owns them. We must never write them, even on a name clash.
PROTECTED_NAMES = {"boot.py", "user_stubs.py"}
PROTECTED_PATTERNS = [
    "*.pyi",
    "codeterraform-*.json",
    "CODE-TERRAFORM-IDE.txt",
    "pyrightconfig*.json",
    "typeshed-LICENSE.txt",
    "*.codeterraform-*.bak",
    "*.codeterraform-*.tmp",
]
PROTECTED_DIRS = {"logs", ".codeterraform", ".vscode", ".zed"}

LOG_LINE = re.compile(r"\[(warn|error)\]", re.IGNORECASE)


@dataclass(frozen=True)
class Action:
    """One planned step. `kind` is create, update, noop, conflict or refuse."""

    kind: str
    target: str
    reason: str = ""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_protected(target: str) -> bool:
    """True when a target path must never be written by this tool."""
    parts = target.split("/")
    name = parts[-1]
    if name in PROTECTED_NAMES or any(part in PROTECTED_DIRS for part in parts[:-1]):
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in PROTECTED_PATTERNS)


def collect_repo_files(repo_root: Path) -> dict[str, bytes]:
    """Map game-relative target path to file bytes for every top-level .py in the source dirs."""
    files: dict[str, bytes] = {}
    for source, prefix in SOURCE_DIRS.items():
        for path in sorted((repo_root / source).glob("*.py")):
            files[prefix + path.name] = path.read_bytes()
    return files


def filter_targets(files: dict[str, bytes], names: list[str]) -> dict[str, bytes]:
    """Keep only targets whose file name (or full target) is in `names`. Empty means all."""
    if not names:
        return files
    wanted = set(names)
    return {
        target: data
        for target, data in files.items()
        if target in wanted or target.rsplit("/", 1)[-1] in wanted
    }


def find_game_edits(
    repo_files: dict[str, bytes],
    game_files: dict[str, bytes | None],
    state: dict[str, str],
) -> list[str]:
    """Targets we wrote that the owner has since changed in game. Help requests are excluded."""
    edits = []
    for target in sorted(repo_files):
        current = game_files.get(target)
        last_written = state.get(target)
        if current is None or last_written is None or is_help_request(current):
            continue
        if sha256(current) != last_written:
            edits.append(target)
    return edits


def read_game_files(game_dir: Path, targets: list[str]) -> dict[str, bytes | None]:
    """Read the current game copy of each target. Missing files map to None."""
    result: dict[str, bytes | None] = {}
    for target in targets:
        path = game_dir / target
        result[target] = path.read_bytes() if path.is_file() else None
    return result


def load_state(path: Path) -> dict[str, str]:
    """Hashes of the files we last wrote. Empty when no sync has run yet."""
    if not path.is_file():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")).get("files", {}))


def save_state(path: Path, state: dict[str, str]) -> None:
    path.write_text(json.dumps({"files": state}, indent=2, sort_keys=True), encoding="utf-8")


def is_help_request(content: bytes) -> bool:
    """True when the game file holds only the owner's "Help me" marker on line 1."""
    lines = content.decode("utf-8", errors="replace").splitlines()
    return (
        bool(lines)
        and lines[0].strip() == HELP_MARKER
        and all(not line.strip() for line in lines[1:])
    )


def plan_one(target: str, wanted: bytes, current: bytes | None, last_written: str | None) -> Action:
    """Decide the action for one target. Pure: no file access."""
    if is_protected(target):
        return Action("refuse", target, "protected name, never written by this tool")
    wanted_hash = sha256(wanted)
    if current is None:
        if last_written is not None:
            return Action("conflict", target, "removed in game since last sync")
        return Action("create", target)
    current_hash = sha256(current)
    if current_hash == wanted_hash:
        return Action("noop", target)
    if is_help_request(current):
        return Action("update", target, "owner asked for help (Help me)")
    # An empty game file (the game's placeholder for a free machine slot) holds nothing to lose.
    if last_written is None and current == b"":
        return Action("create", target, "replaces empty game placeholder")
    if last_written is None:
        return Action("conflict", target, "exists in game and was not written by this tool")
    if current_hash == last_written:
        return Action("update", target)
    return Action("conflict", target, "changed in game since last sync")


def plan_sync(
    repo_files: dict[str, bytes],
    game_files: dict[str, bytes | None],
    state: dict[str, str],
) -> list[Action]:
    """Plan every repo file against the game copy and our record of the last write."""
    return [
        plan_one(target, data, game_files.get(target), state.get(target))
        for target, data in sorted(repo_files.items())
    ]


def apply_actions(
    actions: list[Action],
    repo_files: dict[str, bytes],
    game_dir: Path,
    state: dict[str, str],
) -> dict[str, str]:
    """Write create and update actions atomically and return the new state."""
    new_state = dict(state)
    for action in actions:
        if action.kind not in {"create", "update"}:
            continue
        destination = game_dir / action.target
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".codeterraform-sync.tmp")
        temp.write_bytes(repo_files[action.target])
        # Replace in one step so the game never reads a half-written file.
        os.replace(temp, destination)
        new_state[action.target] = sha256(repo_files[action.target])
    return new_state


def summarize_log(lines: list[str]) -> list[str]:
    """Keep only warn and error lines from a console log."""
    return [line.rstrip("\n") for line in lines if LOG_LINE.search(line)]


def read_fleet_scripts(game_dir: Path) -> dict[str, dict]:
    """Per-script status from the game's fleet file. Read-only; the file is game-owned."""
    path = game_dir / "codeterraform-fleet.json"
    if not path.is_file():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")).get("scripts", {}))


def format_plan(actions: list[Action]) -> str:
    if not actions:
        return "no repo scripts found"
    return "\n".join(
        f"{action.kind:<9} {action.target}" + (f"  ({action.reason})" if action.reason else "")
        for action in actions
    )


def _cmd_plan(game_dir: Path, names: list[str]) -> int:
    repo_files = filter_targets(collect_repo_files(REPO_ROOT), names)
    game_files = read_game_files(game_dir, sorted(repo_files))
    actions = plan_sync(repo_files, game_files, load_state(STATE_FILE))
    print(f"game folder: {game_dir}")
    print(format_plan(actions))
    return 0


def _cmd_apply(game_dir: Path, skip_conflicts: bool, names: list[str]) -> int:
    repo_files = filter_targets(collect_repo_files(REPO_ROOT), names)
    state = load_state(STATE_FILE)
    actions = plan_sync(repo_files, read_game_files(game_dir, sorted(repo_files)), state)
    print(format_plan(actions))
    blocked = [a for a in actions if a.kind in {"conflict", "refuse"}]
    if blocked and not skip_conflicts:
        print(f"refusing to apply: {len(blocked)} conflict or refuse item(s)", file=sys.stderr)
        return 2
    new_state = apply_actions(actions, repo_files, game_dir, state)
    save_state(STATE_FILE, new_state)
    written = sum(1 for a in actions if a.kind in {"create", "update"})
    print(f"wrote {written} file(s)")
    return 0


def _cmd_pull(game_dir: Path, names: list[str]) -> int:
    repo_files = filter_targets(collect_repo_files(REPO_ROOT), names)
    state = load_state(STATE_FILE)
    edits = find_game_edits(repo_files, read_game_files(game_dir, sorted(repo_files)), state)
    if not edits:
        print("no game-side edits to our files")
        return 0
    for target in edits:
        destination = PULL_DIR / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((game_dir / target).read_bytes())
        print(f"pulled {target} -> {destination}")
    return 0


def _cmd_status(game_dir: Path, lines: int) -> int:
    log = game_dir / "logs" / "all.log"
    if log.is_file():
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
        print(f"-- warn/error in last {lines} log lines --")
        for line in summarize_log(tail) or ["(none)"]:
            print(line)
    for name, info in sorted(read_fleet_scripts(game_dir).items()):
        message = info.get("errorMessage") or ""
        print(f"script {name}: {info.get('status')} {message}".rstrip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME_DIR, help="game scripts folder")
    sub = parser.add_subparsers(dest="command")
    plan = sub.add_parser("plan", help="dry run (default)")
    plan.add_argument("--only", nargs="*", default=[], metavar="NAME")
    apply = sub.add_parser("apply", help="write planned changes")
    apply.add_argument("--skip-conflicts", action="store_true", help="write what is safe only")
    apply.add_argument(
        "--only", nargs="*", default=[], metavar="NAME", help="script or Library names"
    )
    pull = sub.add_parser("pull", help="copy game-side edits into .sync-pull/ for review")
    pull.add_argument("--only", nargs="*", default=[], metavar="NAME")
    status = sub.add_parser("status", help="read logs and script status (read-only)")
    status.add_argument("--lines", type=int, default=200, help="log lines to read from the end")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    game_dir: Path = args.game
    if not game_dir.is_dir():
        print(f"game folder not found: {game_dir}", file=sys.stderr)
        return 1
    command = args.command or "plan"
    names = getattr(args, "only", [])
    if command == "apply":
        return _cmd_apply(game_dir, args.skip_conflicts, names)
    if command == "pull":
        return _cmd_pull(game_dir, names)
    if command == "status":
        return _cmd_status(game_dir, args.lines)
    return _cmd_plan(game_dir, names)


if __name__ == "__main__":
    raise SystemExit(main())
