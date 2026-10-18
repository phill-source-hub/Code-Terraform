"""Beat the System: win the Arbiter's 3x3 games back to back and transmit the passcode.

Where it runs: contract script for `beat_the_system` (game root `beat_the_system.py`).
Imports the `arbiter_solver` Library (lib/). Each move wins against every Arbiter tie, so the
    streak does not depend on luck.
Inputs: `self.contract` (BeatTheSystemContract) and `.arbiter` (Arbiter).
API facts relied on (docs/game/manual 327, 328): .arbiter, new_game(), play(cell), board(),
    result(), streak(), target(), token(); get_component("transmitter"), connect(), transmit().
Failure: a game that ends in a loss or draw stops the script before transmitting. The move
    model would be wrong then, and playing on could only lose more streak.
"""

from arbiter_solver import best_move

START_ATTEMPTS = 10
START_WAIT_SECONDS = 0.5

contract = self.contract
arbiter = contract.arbiter


def start_game(arbiter):
    # The manual says new_game() pauses about half a second after a finished game. Retry a
    # bounded number of times in case the board is still busy.
    for _ in range(START_ATTEMPTS):
        status = arbiter.new_game().status
        if status == "ok":
            return
        if status != "in_progress":
            raise RuntimeError("new_game returned " + status)
        sleep(START_WAIT_SECONDS)
    raise RuntimeError("the Arbiter did not start a game")


def play_game(arbiter):
    """Play the current game to its end and return its outcome: win, loss or draw."""
    outcome = arbiter.result()
    while outcome == "ongoing":
        reply = arbiter.play(best_move(arbiter.board()))
        if reply.status not in ("ongoing", "win", "loss", "draw"):
            raise RuntimeError("play returned " + reply.status + ": " + reply.message)
        outcome = reply.status
    return outcome


def run(arbiter):
    """Win games until the streak reaches the target. Returns "" on success, else the reason."""
    target = arbiter.target()
    while arbiter.streak() < target:
        start_game(arbiter)
        outcome = play_game(arbiter)
        if outcome != "win":
            return "a game ended in " + outcome + " at streak " + str(arbiter.streak())
    return ""


try:
    problem = run(arbiter)
except (RuntimeError, ValueError, TypeError) as error:
    print("beat_the_system failed:", error)
else:
    if problem != "":
        print("beat_the_system stopped:", problem)
    else:
        token = arbiter.token()
        if token == "":
            print("beat_the_system: no passcode after the target streak")
        else:
            transmitter = get_component("transmitter")
            transmitter.connect("earth")
            result = transmitter.transmit(contract.id, token)
            print(result.status, result.message)
