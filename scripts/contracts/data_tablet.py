"""Underground Data Tablet: read the hidden message from a 30x30 grid and transmit it.

Where it runs: contract script for `data_tablet` (game root `data_tablet.py`).
Briefing (owner-supplied): probe each cell; distance 0 marks a message cell. Read the message
    cells left to right, top to bottom, and transmit the string.
Method: probe every cell once in row-major order (900 calls for 30x30). Row-major order is the
    reading order, so the message is built in one pass with no sorting.
Failure: a bad probe argument or an empty message is printed and nothing is transmitted.
Self-contained on purpose: no imports (ADR-013).
API facts relied on (docs/game/contracts-data-tablet.md; briefing): self.contract, .id,
    .tablet, tablet.probe(row, col) -> .char / .distance, tablet.rows, tablet.cols,
    get_component("transmitter"), connect(), transmit(), print().
"""

contract = self.contract
tablet = contract.tablet


def read_message(probe, rows, cols):
    message = ""
    for row in range(rows):
        for col in range(cols):
            result = probe(row, col)
            if result.distance == 0:
                message += result.char
    return message


try:
    message = read_message(tablet.probe, tablet.rows, tablet.cols)
except (TypeError, ValueError) as error:
    print("data_tablet failed:", error)
else:
    if message == "":
        print("data_tablet failed: no message cells found")
    else:
        transmitter = get_component("transmitter")
        transmitter.connect("earth")
        result = transmitter.transmit(contract.id, message)
        print(len(message), "chars sent:", result.status, result.message)
