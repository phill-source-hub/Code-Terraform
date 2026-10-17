"""Pure solver for the Orbital Relay Hack contract. No game calls here.

Where it runs: Library named `relay_solver` in game (ADR-030), imported by the contract script.
Inputs: a `probe` callable (the game's `lock.intercept`), tumbler count, and range per tumbler.
Assumptions: each tumbler has exactly one correct value; `intercept` reports each tumbler
    independently. The contract statement does not say `intercept` has an attempt limit
    (UNVERIFIED), so the search is capped at `value_range` probes.
API facts relied on (docs/game/contracts.md): RelayLock.intercept(list[int]) -> list[bool],
    RelayLock.tumblers, RelayLock.range.
"""

from collections.abc import Callable


def solve(
    probe: Callable[[list[int]], list[bool]],
    tumblers: int,
    value_range: int,
) -> list[int]:
    """Find every tumbler's correct value.

    Each probe sets all tumblers to the same candidate. Any tumbler that reports True has
    its correct value at that candidate, so one probe tests a candidate on every tumbler.
    Stops as soon as all tumblers are known. Raises RuntimeError if the range is exhausted
    with a tumbler still unknown, and ValueError if the probe returns the wrong shape.
    """
    solved: list[int | None] = [None] * tumblers
    for candidate in range(value_range):
        if all(value is not None for value in solved):
            break
        hits = probe([candidate] * tumblers)
        if len(hits) != tumblers:
            raise ValueError(f"expected {tumblers} results, got {len(hits)}")
        for index, hit in enumerate(hits):
            if hit and solved[index] is None:
                solved[index] = candidate
    missing = [index for index, value in enumerate(solved) if value is None]
    if missing:
        raise RuntimeError(f"no correct value found for tumblers {missing}")
    return [value for value in solved if value is not None]
