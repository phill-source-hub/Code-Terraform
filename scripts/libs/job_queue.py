"""Choosing which waiting sector job to take. No game calls here.

Where it runs: Library (game `lib/job_queue.py`), used by harvester_1.
Rule: a job wins over the harvester's own plan only when its sector can be reached now (it is
    in the set of sectors affordable this pass). The first such job in queue order is taken,
    so jobs keep their order and an unaffordable job waits instead of being dropped.
Inputs: `pending` as (message id, sector name) pairs, oldest first. Plain values, no game
    objects, so the rule runs in CPython tests.
"""


def pick_job(pending, allowed):
    """The message id of the first pending job whose sector is allowed, or None.

    `pending` items that are not a (id, sector) pair with an integer id are skipped, so a
    malformed message from another script cannot stop the harvester. The integer check also
    rejects a two-character string, which would otherwise unpack as a pair.
    """
    for entry in pending:
        try:
            message_id, sector = entry
        except (TypeError, ValueError):
            continue
        if isinstance(message_id, int) and sector in allowed:
            return message_id
    return None
