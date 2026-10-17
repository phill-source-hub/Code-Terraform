# Contract: Alien Terminal Breach (`terminal_breach`)

Source: owner-supplied briefing text for this contract (build `fe9a45c`). Tag: **VERIFIED (docs)** for the briefing facts below. Feedback rules beyond the briefing, and the probe budget, are UNVERIFIED until the in-game checklist passes.

## Briefing (short form)

- Locked terminal with a 15-digit passcode. Each digit is 1-5.
- `terminal.guess(digits)` returns `GuessResult` with `.correct` (right value, right position) and `.misplaced` (matching values in the wrong position).
- Correct-position matches are removed first. Repeated digits are never over-counted.
- `guess` needs exactly 15 whole numbers in 1-5 as a list. Wrong container or element types raise `TypeError`. Wrong length, fractional values, or out-of-range digits raise `ValueError`.
- `terminal.length` gives the code length (15).
- Answer: transmit the code as a list of whole numbers with the contract id.

## Calls used

| Call | Notes |
|------|-------|
| `self.contract.terminal` | the terminal object |
| `terminal.guess(digits)` | returns `GuessResult` (`.correct`, `.misplaced`) |
| `terminal.length` | 15 |
| `get_component("transmitter")`, `connect("earth")`, `transmit(self.contract.id, code)` | see `docs/game/contracts.md` |

## Method used by the script

Only `.correct` is read. Guess all-`base` once. Then change one position at a time to a candidate digit: the correct count moves +1 (code there is the candidate), -1 (code there is `base`), or 0 (neither). Worst case is 1 + 15 x 4 guesses, plus one final check guess.

## Open questions

- Resolved by X-004 PASS (2026-10-17): `terminal.length` is a property.
- Resolved by X-004 PASS: the `.correct` rule held in game.
- Guess budget or time cost: not in the briefing and not observed as a limit in X-004.
