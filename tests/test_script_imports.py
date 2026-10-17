"""Every game script may import only what the game will resolve.

Game scripts import a Library by its bare name (`from grid import ...`), which the game reads
from `lib/`. A name with no file in scripts/libs/ would fail in game only, so it fails here.
`heapq` is the one documented built-in module we use; anything else must be a repo Library.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIBS = ROOT / "scripts" / "libs"
GAME_SCRIPTS = sorted(
    [*(ROOT / "scripts" / "main").glob("*.py"), *(ROOT / "scripts" / "contracts").glob("*.py")]
)
LIBRARIES = sorted(LIBS.glob("*.py"))
BUILTIN_MODULES = {"heapq"}


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None or node.level:
                names.append("<relative>")
            else:
                names.append(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("script", GAME_SCRIPTS, ids=lambda p: p.name)
def test_script_imports_resolve_to_a_library_or_a_documented_builtin(script):
    for module in _imported_modules(script):
        assert module in BUILTIN_MODULES or (LIBS / f"{module}.py").is_file(), (
            f"{script.name} imports {module!r}, which is neither a documented built-in nor "
            f"a file in scripts/libs/"
        )


@pytest.mark.parametrize("library", LIBRARIES, ids=lambda p: p.name)
def test_library_never_uses_self_or_panel(library):
    # Libraries have no `self` or `panel`; helpers take the component they act for (manual).
    tree = ast.parse(library.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in {"self", "panel"}, f"{library.name}:{node.lineno}"


def test_both_solar_slots_still_have_a_script():
    assert (ROOT / "scripts" / "main" / "solar_1.py").is_file()
    assert (ROOT / "scripts" / "main" / "solar_2.py").is_file()
