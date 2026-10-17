"""Xenogenetics Survey: send every collected DNA sample that is not a known Earth sequence.

Where it runs: contract script for `xenogenetics` (game root `xenogenetics.py`).
Briefing (owner-supplied): 1000 collected samples; 50 Earth reference sequences. Transmit the
    samples that are NOT in the reference, as a list.
Assumptions: matching is exact (same string). Duplicate alien samples are kept, in their
    original order, because the briefing says "all samples". UNVERIFIED: whether Earth expects
    deduplicated output. Check the result status.
Self-contained on purpose: no imports (ADR-013).
API facts relied on (docs/game/contracts.md): self.contract, .id, .earth_ref, .samples
    (list[str]), get_component("transmitter"), connect(), transmit(), print().
"""

contract = self.contract

aliens = []
for sample in contract.samples:
    if sample not in contract.earth_ref:
        aliens.append(sample)

transmitter = get_component("transmitter")
transmitter.connect("earth")
result = transmitter.transmit(contract.id, aliens)
print(len(aliens), "alien samples sent:", result.status, result.message)
