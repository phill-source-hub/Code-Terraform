# Imports and Libraries

Source: in-game DOCS manual, build `fe9a45c`. Sections: "Imports & Libraries", "Player Libraries", "Typing and editor support", "Docstrings". Tag: **VERIFIED (docs)**.

## Research gate

- Library scripts unlock with **Shared Library** research. Unlock path: Ship Computer, then Shared Library.
- Built-in modules and typing support do not need that research.

## Where Libraries live in the game

- Ship → Computer → Library in the left sidebar. Click **+ New**.
- In the repo: `scripts/libs/<name>.py`. Game path: `lib/<name>.py`. Our sync (see README) maps one to the other.

## Importing

```python
from sensors import temp          # one name
from sensors import *             # all public names (names starting with _ are private)
import sensors                    # whole module: sensors.o2()
```

- Library scope is its own. Built-ins and top-level game functions are available. Caller locals are not.
- `self` and `panel` are **not** defined in a Library. Pass a component or id into helpers that act for the caller.
- Docstrings of imported functions show in hover and autocomplete.

## Built-in modules (executable, verified by docs)

Import explicitly, except the global helpers below.

| Module | Used for |
|--------|----------|
| `random` | `random.randint(1, 10)` etc. |
| `re` | regular expressions |
| `json` | records to text and back |
| `heapq` | priority queues |
| `traceback` | where a caught exception came from |
| `math` | `math.gcd`, `math.hypot`, `math.pi` |
| `itertools` | `count`, `islice`, `groupby` |
| `operator` | operators as functions (`add`, `itemgetter`) |
| `string` | constants (`ascii_uppercase`, `digits`) |
| `collections` | `Counter`, `defaultdict`, `OrderedDict`, `deque`, `namedtuple` |
| `enum` | `Enum`, `IntEnum`, `StrEnum`, `Flag`, `auto` |
| `functools` | `reduce`, `partial`, `lru_cache`, `cache`, `cmp_to_key` |
| `dataclasses` | `dataclass`, `field`, `asdict`, `astuple`, `fields`, `replace`, `is_dataclass`, `MISSING` |

Global helpers (no import): `random()`, `rand()`, `randint(min, max)`, `reduce(fn, iterable, initializer?)`, and common math such as `sqrt(x)`, `floor(x)`.

## Typing-only names (erased at run time)

- `typing`, `types`, `collections.abc`, `user_stubs`: annotation names only. Not a place for executable helpers.
- `typing.TYPE_CHECKING` is always `False`.
- `typing.NamedTuple` **does** run: `class Point(NamedTuple):` builds a named tuple.
- `from __future__ import annotations` is a compiler directive. Must be at top of module (after an optional docstring).

## Game types in scope

- `from __builtins__ import Smelter` binds the class. Needed wherever the name runs (`isinstance`, type alias, TypedDict field dict). Not needed for annotations.
- `isinstance(machine, Smelter)` True for a smelter. Every machine is a `Component`. `type_id` = machine type string.
- Stub files (`builtins`, `code_terraform`) are for editor analysis only. A running script cannot import them.
- `user_stubs.py` is type-only. Executable helpers go in a Library.

## Example Library (from manual)

```python
# lib/sensors.py
def temp():
  """Read the current thermometer value."""
  return get_component("thermometer").get_value()

def o2():
  """Read the current oxygen sensor value."""
  return get_component("oxygen_sensor").get_value()
```

```python
# machine script
from sensors import temp
print(temp())
```

## Repo mapping (ours)

- `scripts/libs/*.py` is the source. It is copied to the game's `lib/` by the sync step (pending owner approval).
- Tests import the same file through the fake game harness. A Library must not use `self` or `panel`.
