"""Orbital Relay Hack: find every tumbler's correct value and transmit the full code.

Where it runs: contract script for `relay_hack`. Synced to the game root as `relay_hack.py`
    (contract scripts are `<name>.py` at the root, see docs/game/external-editor.md).
Imports the shared `relay_solver` Library for the solver (ADR-025, ADR-030).
    Shared Library is researched.
Inputs: `self.contract` (RelayHackContract) and `self.contract.lock` (RelayLock).
API facts relied on (docs/game/contracts.md): self.contract, .lock, .id, RelayLock.intercept,
    .tumblers, .range, get_component("transmitter"), connect(), transmit(), print().
Probe budget: at most `lock.range` intercept calls, one per candidate value.
Failure: a probe or search error is printed, nothing is transmitted.
"""

from relay_solver import solve

contract = self.contract
lock = contract.lock


try:
    code = solve(lock.intercept, lock.tumblers, lock.range)
except (RuntimeError, ValueError) as error:
    print("relay_hack failed:", error)
else:
    transmitter = get_component("transmitter")
    transmitter.connect("earth")
    result = transmitter.transmit(contract.id, code)
    print(result.status, result.message)
