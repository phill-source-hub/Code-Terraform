"""Fake in-game API for CPython unit tests.

Scripts run only inside the game, so tests compile a script and `exec` it with a
restricted `__builtins__` dict. That dict holds only the names implemented here,
so a script that calls something we have not faked fails with NameError instead
of quietly using a CPython builtin the game may not have.

Only names declared in the game's stub (VERIFIED for shape) belong here. Add a
name only with a matching test; see docs/api-notes.md.
"""

from __future__ import annotations

import builtins
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Builtins declared in the game's stub (`__builtins__.pyi`). Add a name only when it is in the stub.
GAME_BUILTINS = (
    "len",
    "range",
    "enumerate",
    "all",
    "any",
    "zip",
    "list",
    "str",
    "int",
    "float",
    "bool",
    "sorted",
    "min",
    "max",
    "sum",
    "isinstance",
    "abs",
    "round",
    "repr",
    "chr",
    "ord",
)

# Built-in exception names listed in the game's DOCS manual (build fe9a45c, Exceptions).
GAME_EXCEPTIONS = (
    "ValueError",
    "TypeError",
    "KeyError",
    "IndexError",
    "AttributeError",
    "RuntimeError",
    "NameError",
    "ImportError",
    "ModuleNotFoundError",
    "ZeroDivisionError",
    "StopIteration",
    "GeneratorExit",
    "AssertionError",
    "NotImplementedError",
    "RecursionError",
    "OverflowError",
    "SyntaxError",
    "Exception",
)


@dataclass
class FakeClock:
    """Simulated time. `sleep` advances it instead of blocking."""

    now: float = 0.0

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError(f"cannot move the clock backwards: {seconds}")
        self.now += seconds


@dataclass
class FakeComponent:
    """A machine stand-in. `methods` maps method name to a callable."""

    id: str
    type_id: str
    methods: dict[str, Callable[..., Any]] = field(default_factory=dict)

    def __getattr__(self, name: str) -> Callable[..., Any]:
        # Only called for attributes not set on the dataclass, i.e. game methods.
        methods = self.__dict__.get("methods", {})
        if name in methods:
            return methods[name]
        raise AttributeError(f"fake component {self.id!r} has no method {name!r}")


@dataclass
class FakeGame:
    """Records everything a script sends to the game so tests can assert on it."""

    clock: FakeClock = field(default_factory=FakeClock)
    components: dict[str, FakeComponent] = field(default_factory=dict)
    printed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    statuses: list[tuple[str, str]] = field(default_factory=list)
    notifications: list[tuple[str, str]] = field(default_factory=list)

    def print(self, *values: object, sep: str = " ", end: str = "\n") -> None:
        self.printed.append(sep.join(str(v) for v in values) + end)

    def sleep(self, seconds: float, /) -> None:
        self.clock.advance(seconds)

    def warn(self, *values: object, sep: str = " ", end: str = "\n") -> None:
        self.warnings.append(sep.join(str(v) for v in values) + end)

    def set_status(self, message: str, level: str = "info") -> None:
        # The game rejects a status that is empty, longer than 240 characters or holds a null
        # character, and stops the script. Enforce the same rule so tests catch it.
        if not message or len(message) > 240 or "\x00" in message:
            raise ValueError(
                "Status message must contain non-empty text of at most 240 characters, "
                "without null characters."
            )
        self.statuses.append((message, level))

    def notify(self, text: str, /, level: str = "info", **_: Any) -> None:
        self.notifications.append((text, level))

    def get_component(self, name: str, /) -> FakeComponent | None:
        return self.components.get(name)

    def builtins(self) -> dict[str, Any]:
        """The only names a script can see. Anything else raises NameError."""
        return {
            # Libraries load through CPython's import here; tests put scripts/libs on sys.path.
            # The game's own loader is UNVERIFIED beyond the manual's examples.
            "__import__": builtins.__import__,
            "print": self.print,
            "warn": self.warn,
            "sleep": self.sleep,
            # Common builtins declared in the game stub (VERIFIED stub).
            **{name: getattr(builtins, name) for name in GAME_BUILTINS},
            # Exception names the game supports (DOCS, Exceptions section).
            **{name: getattr(builtins, name) for name in GAME_EXCEPTIONS},
            "set_status": self.set_status,
            "notify": self.notify,
            "get_component": self.get_component,
        }


def run_script(
    source: str,
    game: FakeGame,
    filename: str = "<script>",
    extra_globals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile and run `source` against `game`. Returns the script's globals.

    `extra_globals` injects script-owner names the game provides, such as `self`
    for a contract script.
    """
    namespace: dict[str, Any] = {"__builtins__": game.builtins(), "__name__": "__main__"}
    namespace.update(extra_globals or {})
    code = compile(source, filename, "exec")
    exec(code, namespace)
    return namespace
