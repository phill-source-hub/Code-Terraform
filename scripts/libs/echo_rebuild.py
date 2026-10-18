"""Pure rebuild of the Three Echoes signal from its three frequency fragments. No game calls.

Where it runs: Library `echo_rebuild` in game (lib/), imported by the Three Echoes contract.
Inputs: `freq_a`, `freq_b`, `freq_c` strings from `ThreeEchoesBroadcast`.
Assumptions: freq_a holds characters 1, 4, 7 ... of the original (1-based), freq_b holds 2, 5,
    8 ... and freq_c holds 3, 6, 9 ... (manual, Three Echoes). Taking one character from each
    fragment in turn therefore restores the original order, whatever the lengths are.
API facts relied on (docs/game/manual Three Echoes Broadcast, 355): .freq_a, .freq_b, .freq_c.
"""


def rebuild_signal(freq_a, freq_b, freq_c):
    """Interleave the three fragments back into the original signal.

    Raises TypeError when a fragment is not a string. A fragment that is longer than the others
    simply contributes its tail at the end.
    """
    fragments = (freq_a, freq_b, freq_c)
    for fragment in fragments:
        if not isinstance(fragment, str):
            raise TypeError("each frequency fragment must be a string")
    longest = max(len(fragment) for fragment in fragments)
    pieces = []
    for index in range(longest):
        for fragment in fragments:
            if index < len(fragment):
                pieces.append(fragment[index])
    return "".join(pieces)
