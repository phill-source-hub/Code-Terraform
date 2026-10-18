"""Game scripts may call only names the game provides, so a set() or frozenset() fails in game only.

The Control Room Library and cards are checked here: every called name must be a game builtin
(GAME_BUILTINS in the harness, from the stub), an injected name, or defined or imported in the file.
"""

import ast
from pathlib import Path

from tests.harness.fake_game import GAME_BUILTINS

ROOT = Path(__file__).resolve().parent.parent
GAME_INJECTED = {"get_component", "panel", "print", "sleep", "warn", "set_status", "notify", "self"}
CHECKED = [
    ROOT / "scripts" / "libs" / "control_room.py",
    *sorted((ROOT / "scripts" / "cards").glob("*.py")),
]


def unknown_calls(source):
    tree = ast.parse(source)
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.alias):
            defined.add(node.asname or node.name)
        elif isinstance(node, ast.arg):
            defined.add(node.arg)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    return sorted(called - set(GAME_BUILTINS) - GAME_INJECTED - defined)


def test_detector_flags_a_name_the_game_does_not_have():
    assert unknown_calls("RED = frozenset({'a'})\n") == ["frozenset"]


def test_detector_accepts_builtins_defined_names_and_imports():
    source = (
        "from control_room import short_text\ndef f(x):\n    return short_text(str(len(x)), 3)\n"
    )
    assert unknown_calls(source) == []


def test_control_room_library_and_cards_use_only_game_names():
    for path in CHECKED:
        assert unknown_calls(path.read_text(encoding="utf-8")) == [], path.name
