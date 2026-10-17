# Language: basics, output, self, errors, loops

Source: in-game DOCS manual, build `fe9a45c`. Sections: Getting Started, Variables, Print, Self & Components, Loops & Scripts, Exceptions, Docstrings, Command Results, Long-Running Scripts. Tag: **VERIFIED (docs)**. Short notes, own words.

## Ground rule

The language is Python-like. Do not assume CPython. Names the game does not list here are UNVERIFIED until checked in `api-notes`. Stub `__builtins__.pyi` (generated, in the game folder) is the list of what exists.

## Output

- `print(*values)` normal output. Multiple values are space-separated.
- `warn(...)` stands out in the persistent console, no toast.
- `debug(...)` shown only when debug output is enabled in console options.
- Console can filter: this script, all output, warnings, or errors.
- Log file: `logs/all.log` in the scripts folder (see `CODE-TERRAFORM-IDE.txt`).

## Scripts run once; loops keep them alive

- A script runs once unless it loops.
- VERIFIED (docs): the interpreter yields to the game during `while` loops, so a loop does not block the world. `sleep(seconds)` is for deliberate pacing, not safety.
- `for i in range(n):` iterates a list.

## `self` and components

- Most scripts run inside a machine. Inside, `self` = this machine.
- Hardware actions (move, analyze, transfer) are usually **self only**. Store the result, branch on `.status`, read `.message`.
- `get_component(id)` for read-only access to another machine (for example `get_component("scanner_1").get_scanned()`).
- Local actions can take another component as an argument (for example `self.take_from(collector)`). The action still belongs to `self`, not remote control.
- Use stable ids for long-running scripts. Display names can change.

## Command results (the result contract)

- A world-changing command returns a result object, not a boolean.
- Fields: `.status` (stable code, branch on this), `.message` (player text, never branch on it).
- Payload fields exist only for documented statuses. Read them after `status == "ok"`.
- Result objects are always truthy. Do not write `if self.analyze():`.
- Success is not always `"ok"`. Others include `"started"`, `"queued"`, `"charging"`, `"complete"`. Check the command's outcome table.
- `"busy"` is a transient outcome for commands that define it. Wait, then retry. Do not retry all non-success statuses.
- Queries (`is_running()`, `count()`, `tier()`) return natural values directly, not results.
- Some commands **yield** (script pauses until done, e.g. `analyze()`). Others **start or queue** work and return at once (e.g. `charge(...)` returns `"charging"` or `"queued"`). The command entry says which.

## Long-running scripts

- On game load a running script restarts from its first line. Local variables, call stack and line position are not kept. Saved script source and running status are kept.
- World state (cargo, specimen, queued jobs) persists and is the starting point.
- Build a reconciliation loop: read the machine state, decide the missing step, attempt once, check `.status`, wait after transient blockers, repeat.
- Do not depend on a local variable to remember machine contents. Re-read.
- Before a write (transfer, buy, queue), inspect what is already there and calculate the missing amount.
- Persistent knowledge across stops or loads: use the **Data Archive** (see manual, "Data Archive"). Not yet extracted.

## Variables and operators

- `x = 10`, `name = "oxygen"`, `active = True`. Standard.
- Assignment is `=`; equality is `==`. Standard.
- Membership and `None` checks: standard forms. Detail in manual "Operators" (not extracted in full).

## Exceptions

- Use exceptions for bugs and malformed calls only: wrong argument kind raises `TypeError`; right kind, wrong value raises `ValueError`.
- Expected world outcomes (cargo full, nothing scanned, queue empty) are **result statuses**, not exceptions.
- `try` / `except Name as error` / `else` / `finally`. The `as` name is cleared when the handler exits.
- Bare `raise` re-raises. `raise X from cause` sets `__cause__`.
- Built-in names listed as supported: `NameError`, `UnboundLocalError`, `ImportError`, `ModuleNotFoundError`, `ZeroDivisionError`, `StopIteration`, `GeneratorExit`, `AssertionError`, `NotImplementedError`, `RecursionError`, `IndentationError`, `OverflowError`, `SyntaxError`, plus common `ValueError`, `TypeError`, `KeyError`, `IndexError`, `AttributeError`, `RuntimeError`.
- Own exceptions: subclass `Exception`. Example in manual (`LowBattery`).
- Avoid broad `except Exception` except at a boundary. It can hide bugs.

## Docstrings

- String literal under `def` = function docstring. Shown in hover and autocomplete. Supports markdown-lite: `## Returns`, bullets, tables (needs separator row), fenced code.
- A triple-quoted string at file top = script description. Variants tab uses its first non-empty line. If absent, the first `#` comment is used.

## Error and status reporting

- `set_status(message, level)` for the script run. Message ≤240 chars, no nulls. Level `info`, `warn`, `error`.
- `notify(...)` for toasts. Use sparingly. See `api-notes.md` for duration rules.

## Not yet extracted from the manual

- Operators in detail, Numbers, Conversion functions, Strings and f-strings, Regular expressions (module `re`), Lists/tuples/dicts, Match/case, Functions, Generators, Caching, Classes and dataclasses, Enums, Decorators, `@property`, Built-in function list, stdlib module references (`random`, `functools`, `re`, `dataclasses`, `enum`, `json`, `heapq`, `traceback`, `math`, `itertools`, `operator`, `string`, `collections`), Code Editor, Debug mode.
- These are needed as scripts use them. Add a file per area when needed.
