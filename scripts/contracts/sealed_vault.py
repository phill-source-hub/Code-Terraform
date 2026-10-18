"""Sealed Vault: walk the maze from (0, 0) to the exit, open the vault and transmit the key.

Where it runs: contract script for `sealed_vault` (game root `sealed_vault.py`).
Imports the `maze_solver` Library (lib/). The walk tracks its own position from the start, so it
    does not need to know the compass layout of the maze.
Inputs: `self.contract` (SealedVaultContract) and `.vault` (Vault).
API facts relied on (docs/game/manual 346, 347): .vault, .size, move(direction) with statuses
    "path", "wall", "exit"; escape() with statuses "ok", "not_at_exit" and the .key payload.
UNVERIFIED: the transmitted value is the key from escape(). The manual does not state the answer
    format; confirm against the in-game briefing before the first run (in-game-test-log, CT-002).
    A wrong answer is safe to retry.
Failure: a blocked walk or a refused escape is printed and nothing is transmitted.
"""

from maze_solver import find_exit

contract = self.contract
vault = contract.vault

try:
    path = find_exit(
        lambda direction: vault.move(direction).status, vault.size * vault.size * 4 + 4
    )
except (RuntimeError, ValueError, TypeError) as error:
    print("sealed_vault failed:", error)
else:
    opened = vault.escape()
    if opened.status != "ok":
        print("sealed_vault escape:", opened.status, opened.message)
    else:
        print("sealed_vault: exit in", len(path), "moves")
        transmitter = get_component("transmitter")
        transmitter.connect("earth")
        result = transmitter.transmit(contract.id, opened.key)
        print(result.status, result.message)
