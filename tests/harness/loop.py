"""Helpers for scripts that loop forever.

A game script ends only when it is stopped. In tests the loop is stopped by raising
`ScriptStop` from a fake call the test is checking, so one pass is enough to assert on.
"""

from pathlib import Path
from typing import Any

from tests.harness.fake_game import FakeGame, run_script


class ScriptStop(Exception):
    """Raised by a fake to end a looping script after the call under test."""


def stop_after(record: list, value: Any = None, *, name: str = "call"):
    """Return a fake method that records its arguments, then stops the script."""

    def fake(*args, **kwargs):
        record.append((name, args, kwargs))
        raise ScriptStop

    return fake


def run_loop(path: Path, game: FakeGame, owner: Any, extra: dict[str, Any] | None = None) -> None:
    """Run a looping machine script until a fake raises ScriptStop."""
    namespace = {"self": owner, **(extra or {})}
    try:
        run_script(
            path.read_text(encoding="utf-8"), game, filename=str(path), extra_globals=namespace
        )
    except ScriptStop:
        return


class StopOnSleep(FakeGame):
    """Game whose sleep ends the pass. A blocked path sleeps, so the test ends there."""

    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        raise ScriptStop
