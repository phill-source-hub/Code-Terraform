"""Heat generator controller: finds each thermal state's best power once, then holds it.

Where it runs: the Mk I heat generator slot `heater_1`. Self-contained on purpose, like the
    o2gen and pressure controllers (ADR-034): no imports, and `self` is the heater it runs on.
Rules (manual, Heat Generator and Tier 3 Progression):
    the best positive set_power() value depends on thermal_state(), which is fixed for one game
    day. efficiency() reads 100% only at that value and about 31% one step away. The manual
    gives no optimum, so the script finds it. set_power(0) turns heating off.
Policy, every pass, paced by PASS_SECONDS:
    1. read thermal_state() (never cached, so a new day is seen on the next pass);
    2. a state with a known optimum: set_power(optimum);
    3. a state with no known optimum: probe 0.1 to 10.0 in order, one set_power and one read per
       probe, and keep the first probe that reads NEAR_FULL. The scan is discarded if the state
       changes mid-scan, since its readings belong to the old state;
    4. a state whose full scan finds nothing: set_power(0) and warn. It is not rescanned until
       the script restarts.
Status shows state, power, efficiency and output. It is set only when its text changes.
Failure: a rejected set_power is printed as a warning once per status change.
The optimum table lives in this run only. A game reload or restart runs the scan again.
API facts relied on (manual, Heat Generator): self.set_power(watts) (.status), self.thermal_state(),
    self.efficiency(), self.output(); set_status, print, sleep.
"""

PASS_SECONDS = 1
# Wait before reading efficiency after each probe. The manual does not say how fast it updates, so
# this is a guess; in-game check H-001 in docs/in-game-test-log.md.
SETTLE_SECONDS = 1
# Probes are 0.1 apart from 0.1 to 10.0, the manual's clamp range. The peak width is not in the
# manual, so 0.1 is a guess; the spec lists this as an owner question.
SCAN_STEPS = 100
# The manual says exactly 100% at the optimum and about 31% one step away. 99.5 absorbs float
# rounding in the game's efficiency value without matching a neighbouring step.
NEAR_FULL = 99.5

best = {}
no_optimum = []
last_status = None
# Holds the last set_power status, so a fault is warned once and again only after a clean call.
last_power = {"status": None}


def check_power_call(result):
    """Warn once per fault; a clean call clears the record so the next fault warns again."""
    if result.status != "ok" and result.status != last_power["status"]:
        print("warning: set_power " + result.status)
    last_power["status"] = result.status


def scan_for(state):
    """Return (outcome, power) for state. Outcome is "found", "missing", "changed" or "rejected"."""
    for step in range(1, SCAN_STEPS + 1):
        # Division keeps the probe at the nearest float to 0.1, 0.2 ... 10.0, so a game-side
        # exact match is not lost to accumulated rounding.
        power = step / 10
        result = self.set_power(power)
        check_power_call(result)
        # A rejected probe did not set the power, so its reading would be 0% for the wrong reason.
        # Abort; the next pass retries the scan.
        if result.status != "ok":
            return "rejected", None
        sleep(SETTLE_SECONDS)
        reading = self.efficiency()
        # Check the state after the read: a day change between the two reads makes the reading
        # belong to the old state, so it is thrown away.
        if self.thermal_state() != state:
            return "changed", None
        if reading >= NEAR_FULL:
            return "found", power
    return "missing", None


def apply_power(power):
    check_power_call(self.set_power(power))


while True:
    state = self.thermal_state()

    if state in best:
        apply_power(best[state])
    elif state in no_optimum:
        apply_power(0)
    else:
        set_status("scanning power for " + state, "info")
        outcome, power = scan_for(state)
        if outcome == "found":
            best[state] = power
            print("best power for " + state + ": " + str(power))
        elif outcome == "missing":
            no_optimum.append(state)
            apply_power(0)
            print("warning: no power reached 100% for " + state + "; heater off for this state")
        # "changed" and "rejected" leave the state unknown, so the next pass tries again.

    status = (
        "state "
        + state
        + " power "
        + str(best.get(state, 0))
        + " efficiency "
        + str(round(self.efficiency(), 1))
        + "% output "
        + str(round(self.output(), 2))
    )
    if status != last_status:
        set_status(status, "info")
        last_status = status
    sleep(PASS_SECONDS)
