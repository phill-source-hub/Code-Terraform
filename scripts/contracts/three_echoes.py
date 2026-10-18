"""Three Echoes: rebuild the signal from its three frequency fragments and transmit it.

Where it runs: contract script for `three_echoes` (game root `three_echoes.py`).
Imports the `echo_rebuild` Library (lib/).
Inputs: `self.contract` (ThreeEchoesContract) and `.broadcast` (ThreeEchoesBroadcast).
API facts relied on (docs/game/manual 354, 355): .broadcast, .freq_a, .freq_b, .freq_c; the
    fragments take characters 1,4,7... / 2,5,8... / 3,6,9... of the original.
UNVERIFIED: the transmitted value is the whole rebuilt string. The manual does not state the
    answer format; confirm against the in-game briefing before the first run (CT-003). A wrong
    answer is safe to retry.
Failure: a non-string fragment is printed and nothing is transmitted.
"""

from echo_rebuild import rebuild_signal

contract = self.contract
broadcast = contract.broadcast

try:
    signal = rebuild_signal(broadcast.freq_a, broadcast.freq_b, broadcast.freq_c)
except TypeError as error:
    print("three_echoes failed:", error)
else:
    print("three_echoes: rebuilt", len(signal), "characters")
    transmitter = get_component("transmitter")
    transmitter.connect("earth")
    result = transmitter.transmit(contract.id, signal)
    print(result.status, result.message)
