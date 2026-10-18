"""Pure depth-first walk to the exit of a maze that only reports what each step did. No game
calls here.

Where it runs: Library `maze_solver` in game (lib/), imported by the Sealed Vault contract.
Inputs: `move(direction)` returns the status string of one step ("path", "wall" or "exit").
Assumptions: the start is a path cell, the exit is reached by stepping onto it, and a wall
    leaves the position unchanged. Positions are tracked here by offset from the start, so the
    solver never needs to know which compass direction is which row or column.
API facts relied on (docs/game/manual Vault, 347): Vault.move(direction) statuses "path",
    "wall", "exit"; Vault.size; the position resets to the start at each script run.
"""

OFFSETS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
ORDER = ("north", "east", "south", "west")


def find_exit(move, max_moves):
    """Return the directions that walk from the start onto the exit.

    Depth-first with backtracking: each cell is entered once, and a dead end is left by
    stepping back the way it was entered. `max_moves` caps every call to `move`, so a
    misreported maze stops the walk instead of looping. Raises RuntimeError when the walk
    runs out of cells or moves, and ValueError on a status the manual does not list.
    """
    moves = 0

    def step(direction):
        # Every call to the game counts, including the steps back out of dead ends.
        nonlocal moves
        if moves >= max_moves:
            raise RuntimeError(f"gave up after {max_moves} moves")
        moves += 1
        return move(direction)

    position = (0, 0)
    visited = {position}
    next_option = {position: 0}
    stack = []

    while True:
        advanced = False
        while next_option[position] < len(ORDER):
            direction = ORDER[next_option[position]]
            next_option[position] += 1
            dx, dy = OFFSETS[direction]
            target = (position[0] + dx, position[1] + dy)
            if target in visited:
                continue
            status = step(direction)
            if status == "wall":
                continue
            if status == "exit":
                return stack + [direction]
            if status != "path":
                raise ValueError(f"unknown move status {status!r}")
            visited.add(target)
            next_option[target] = 0
            stack.append(direction)
            position = target
            advanced = True
            break
        if advanced:
            continue
        if not stack:
            raise RuntimeError("exit not reachable from the start")
        back = OPPOSITE[stack.pop()]
        if step(back) != "path":
            raise RuntimeError("could not step back along the walked path")
        dx, dy = OFFSETS[back]
        position = (position[0] + dx, position[1] + dy)
