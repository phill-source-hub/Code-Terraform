"""Orbital Relay Hack: find every tumbler's correct value and transmit the full code.

Where it runs: contract script for `relay_hack`. Paste into the game's contract editor.
    UNVERIFIED: how a contract script is attached in game. Not synced by tools/sync_to_game.py.
Inputs: `self.contract` (RelayHackContract) and `self.contract.lock` (RelayLock).
Assumptions: `relay_hack` Library is available as game `lib/relay_hack.py`.
API facts relied on (docs/game/contracts.md): self.contract, .lock, .id, RelayLock.intercept,
    .tumblers, .range, get_component("transmitter"), connect(), transmit(), print().
Failure: a probe or search error is printed, nothing is transmitted.
"""

from relay_hack import solve

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
