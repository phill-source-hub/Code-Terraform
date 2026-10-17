# Spec: Oxygen Generator (o2gen_1)

Status: revised 2026-10-17 to the owner's requirements. Source: owner-supplied in-game text for o2gen_1 and the manual (build fe9a45c).

- **Goal**: peak efficiency (100%) on the Mk I generator, with no waste penalty.
- **Intake**: exactly CO2 / 10 (ppt), unrounded, read from `get_component("atmosphere").get_co2()` every pass.
- **Waste**: dump only when waste is between 50 and 60 (inclusive). Never dump outside that window: a penalty is not accepted.
- **Running**: the loop has no sleep. The game yields during loops, so it runs continually. No rate assumption is made.
- **Waste above 60**: the script does not dump. It shows one warning per excursion above 60 and keeps running. Owner decision needed on what to do then (see open questions).
- **Success**: efficiency reads 100% with waste at or below 60. Every dump is at 50-60 and reports penalty 0. Waste never reaches 100.

## Open questions (owner)

- Waste above 60 cannot be cleared without a penalty, and the manual shows no other way to lower it. Options: (a) accept the penalty only as a last resort, (b) lower intake while waste is near 60 to slow new waste, which costs efficiency briefly, (c) pause the generator. The script currently takes none of these.
- The loop runs without pacing, so the game's own step budget sets the sampling rate. Check in game that waste is dumped inside 50-60 each time, and never jumps past 60 between reads.
