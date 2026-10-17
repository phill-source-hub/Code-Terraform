"""Alien Terminal Breach: crack the 15-digit passcode (digits 1-5) and transmit it.

Where it runs: contract script for `terminal_breach` (game root `terminal_breach.py`).
Briefing (owner-supplied): guess() returns .correct and .misplaced. Only .correct is used here.
Method: guess all-`base` once to get how many positions hold `base`. Then, for each position,
    change only that position to a candidate digit. The correct count moves by +1 when the
    code there is the candidate, -1 when it is `base`, and 0 otherwise. Worst case is
    1 + 15 * 4 = 61 guesses, plus one final check guess.
Why not .misplaced: repeated digits make it hard to reason about with a single probe; .correct
    alone gives an exact per-position answer.
Failure: a bad guess or an inconsistent answer is printed and nothing is transmitted.
Self-contained on purpose: no imports (ADR-013).
API facts relied on (docs/game/contracts-terminal-breach.md; briefing): self.contract, .id,
    .terminal, terminal.length, terminal.guess(digits) -> .correct, get_component("transmitter"),
    connect(), transmit(), print().
"""

contract = self.contract
terminal = contract.terminal
DIGITS = [1, 2, 3, 4, 5]


def solve(count_correct, length, digits):
    base = digits[0]
    base_correct = count_correct([base] * length)
    code = []
    for position in range(length):
        found = None
        for candidate in digits[1:]:
            probe = [base] * length
            probe[position] = candidate
            delta = count_correct(probe) - base_correct
            if delta == 1:
                found = candidate
                break
            if delta == -1:
                found = base
                break
        if found is None:
            raise RuntimeError("no digit found at position " + str(position))
        code.append(found)
    return code


def count_correct(digits):
    return terminal.guess(digits).correct


try:
    code = solve(count_correct, terminal.length, DIGITS)
    if count_correct(code) != terminal.length:
        raise RuntimeError("solved code did not verify")
except (TypeError, ValueError, RuntimeError) as error:
    print("terminal_breach failed:", error)
else:
    transmitter = get_component("transmitter")
    transmitter.connect("earth")
    result = transmitter.transmit(contract.id, code)
    print(result.status, result.message)
