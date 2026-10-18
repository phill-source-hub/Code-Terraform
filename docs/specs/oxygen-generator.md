# Spec: Oxygen Generator (o2gen_1)

Status: revised 2026-10-17 to the owner's requirements. Source: owner-supplied in-game text for o2gen_1 and the manual (build fe9a45c).

- **Goal**: peak efficiency (100%) on the Mk I generator, with no waste penalty.
- **Intake**: exactly CO2 / 10 (ppt), unrounded, read from `get_component("atmosphere").get_co2()` every pass.
- **Waste**: dump only when waste is between 50 and 60 (inclusive). Never dump outside that window: a penalty is not accepted.
- **Running**: the loop has no sleep. The game yields during loops, so it runs continually. No rate assumption is made.
- **Waste above 60**: the script does not dump. It shows one warning per excursion above 60 and keeps running.
- **Last resort at 90**: once waste reaches LAST_RESORT (90, owner-set, not a manual value), the script dumps and accepts the penalty. It warns with the penalty. Ninety leaves headroom below the stall at 100.
- **Success**: efficiency reads 100% with waste at or below 60. Every dump is at 50-60 and reports penalty 0. Waste never reaches 100.

## Open questions (owner)

- Last-resort threshold: 90 is an owner-accepted failsafe, not a manual value (accepted 2026-10-18). Waste above 60 is not dumped until 90; at 90 the dump takes the penalty so the generator does not stall at 100. Value in `scripts/main/o2gen_1.py`.
- Option (b), lowering intake near 60 to slow new waste, and option (c), pausing the generator, are not implemented.
- The loop runs without pacing, so the game's own step budget sets the sampling rate. Check in game that waste is dumped inside 50-60 each time, and never jumps past 60 between reads.
