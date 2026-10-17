"""Harvester's record of sectors already visited in the current scan pass. No game calls here.

Where it runs: Library (game `lib/trip_log.py`), used by harvester_1.
Why a pass number: scanner_1 saves a new map once per complete pass and bumps `scanner.pass`.
    A sector collected or found empty under the old map may hold items under the new one, so
    the log starts again when the pass number changes (backlog B-004).
Stored form (Data Archive key `harvester.done`): {"pass": int, "sectors": [sector names]}.
Shape check: `dict` is not in the stub-verified builtins, so the check indexes the value rather
    than calling isinstance(value, dict). `isinstance` with `list` is stub-verified and used.
"""


def new_log(pass_number):
    return {"pass": pass_number, "sectors": []}


def reconcile(stored, pass_number):
    """The log to use for this pass: the stored one if it belongs to pass_number, else a fresh one.

    Anything that is not a log of ours (None, a number, a string, a list) is discarded, so a
    corrupt or missing entry costs a re-visit, never a crash.
    """
    try:
        same_pass = stored["pass"] == pass_number
        sectors = stored["sectors"]
    except (TypeError, KeyError):
        return new_log(pass_number)
    if same_pass and isinstance(sectors, list):
        return stored
    return new_log(pass_number)


def mark_done(log, sector):
    """A copy of `log` with `sector` added. The input is never changed, so a failed save retries."""
    if sector in log["sectors"]:
        return log
    return {"pass": log["pass"], "sectors": log["sectors"] + [sector]}


def is_done(log, sector):
    return sector in log["sectors"]
