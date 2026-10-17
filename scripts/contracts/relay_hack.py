"""Orbital Relay Hack: find every tumbler's correct value and transmit the full code.

Where it runs: contract script for `relay_hack`. Synced to the game root as `relay_hack.py`
    (contract scripts are `<name>.py` at the root, see docs/game/external-editor.md).
Self-contained on purpose: no imports. Library imports need Shared Library research, which
    this save does not have yet. The solver is a copy of scripts/libs/relay_hack.py. Tests check
    the copy finds the right code on the same inputs; they do not diff the source text.
Inputs: `self.contract` (RelayHackContract) and `self.contract.lock` (RelayLock).
API facts relied on (docs/game/contracts.md): self.contract, .lock, .id, RelayLock.intercept,
    .tumblers, .range, get_component("transmitter"), connect(), transmit(), print().
Probe budget: at most `lock.range` intercept calls, one per candidate value.
Failure: a probe or search error is printed, nothing is transmitted.
"""

contract = self.contract
lock = contract.lock


def solve(probe, tumblers, value_range):
    solved = [None] * tumblers
    for candidate in range(value_range):
        if all(value is not None for value in solved):
            break
        hits = probe([candidate] * tumblers)
        if len(hits) != tumblers:
            raise ValueError("expected " + str(tumblers) + " results, got " + str(len(hits)))
        for index, hit in enumerate(hits):
            if hit and solved[index] is None:
                solved[index] = candidate
    missing = [index for index, value in enumerate(solved) if value is None]
    if missing:
        raise RuntimeError("no correct value found for tumblers " + str(missing))
    return solved


try:
    code = solve(lock.intercept, lock.tumblers, lock.range)
except (RuntimeError, ValueError) as error:
    print("relay_hack failed:", error)
else:
    transmitter = get_component("transmitter")
    transmitter.connect("earth")
    result = transmitter.transmit(contract.id, code)
    print(result.status, result.message)
