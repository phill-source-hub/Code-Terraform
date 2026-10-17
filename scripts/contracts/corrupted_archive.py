"""Corrupted Archive: pair up the 50 matching words in a 10x10 grid and transmit the pairs.

Where it runs: contract script for `corrupted_archive` (game root `corrupted_archive.py`).
Briefing (owner-supplied): each cell holds a word; 50 unique words, each exactly twice. Transmit
    [row1, col1, row2, col2] for every pair. Pairs in any order, either cell first.
Method: read every cell once (100 flips, row-major). The first sighting of a word is stored;
    the second sighting makes a pair. Read-only queries, so no game time is spent on writes.
Failure: if any word lacks a partner, or the pair count is wrong, the script prints the problem
    and transmits nothing.
Self-contained on purpose: no imports (ADR-013).
API facts relied on (docs/game/contracts.md; briefing): self.contract, .id, .archive,
    archive.rows, archive.cols, archive.flip(row, col) -> word, get_component("transmitter"),
    connect(), transmit(), print().
"""

archive = self.contract.archive
seen = {}
pairs = []

for row in range(archive.rows):
    for col in range(archive.cols):
        word = archive.flip(row, col)
        if word in seen:
            first = seen.pop(word)
            pairs.append([first[0], first[1], row, col])
        else:
            seen[word] = [row, col]

expected_pairs = archive.rows * archive.cols // 2
if seen:
    print("corrupted_archive failed: unmatched words", len(seen))
elif len(pairs) != expected_pairs:
    print("corrupted_archive failed: found", len(pairs), "pairs, expected", expected_pairs)
else:
    transmitter = get_component("transmitter")
    transmitter.connect("earth")
    result = transmitter.transmit(self.contract.id, pairs)
    print(len(pairs), "pairs sent:", result.status, result.message)
