"""Shared test setup.

Game scripts import Libraries by bare module name (`from grid import ...`), which the game
resolves from its `lib/` folder. Here the same names resolve from scripts/libs/, so every test
can import a script that uses a Library.
"""

from pathlib import Path

import pytest

LIBS = Path(__file__).resolve().parent.parent / "scripts" / "libs"


@pytest.fixture(autouse=True)
def _library_path(monkeypatch):
    monkeypatch.syspath_prepend(str(LIBS))
