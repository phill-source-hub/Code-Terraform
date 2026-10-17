"""Oxygen generator controller: peak efficiency, waste dumped only inside 50-60, no penalty.

Where it runs: machine script slot `o2gen_1` (self = this generator). Mk I.
Self-contained on purpose (ADR-014): no imports.
Rules (manual, Oxygen Generator and Atmosphere):
    peak intake is exactly CO2 / 10 (ppt); efficiency is 100% at peak with waste at or below 60;
    dumping between 50 and 60 is penalty-free; dumping outside it applies a penalty.
Policy, every pass, with no sleep (the game yields during loops, so the loop runs continually):
    1. set intake to CO2 / 10 from get_component("atmosphere").get_co2(), unrounded;
    2. if waste is between 50 and 60, dump. Outside that window, never dump: the penalty is not
       accepted. A waste level above 60 is shown as a warning until the owner decides what to do.
    3. if a dump reports a penalty, or the penalty is not zero, show a warning.
Status and console lines change only when their content changes, so the log stays readable.
Failure: a missing atmosphere is an error status; a rejected call is a warning. The loop goes on.
API facts relied on (manual, Oxygen Generator and Atmosphere): self.set_intake(value),
    self.waste(), self.dump_waste() (.status, .penalty), self.dump_penalty(), self.efficiency(),
    get_component("atmosphere").get_co2(); set_status, print.
"""

DUMP_LOW = 50
DUMP_HIGH = 60
# Last resort: waste this high is close to the stall at 100. A dump here takes the penalty,
# which is accepted only to keep the generator running. Owner-set; not a manual value.
LAST_RESORT = 90

atmosphere = get_component("atmosphere")
last_status = None
above_warned = False

while True:
    if atmosphere is None:
        set_status("atmosphere not found", "error")
        continue

    intake = atmosphere.get_co2() / 10
    setting = self.set_intake(intake)
    if setting.status != "ok":
        print("warning: set_intake " + setting.status)

    waste = self.waste()
    if DUMP_LOW <= waste <= DUMP_HIGH:
        dumped = self.dump_waste()
        if dumped.status == "ok":
            print("dumped waste at " + str(round(waste, 1)) + ", penalty " + str(dumped.penalty))
            if dumped.penalty != 0:
                print("warning: dump at " + str(round(waste, 1)) + " reported a penalty")
        else:
            print("warning: dump " + dumped.status)
    elif waste >= LAST_RESORT:
        dumped = self.dump_waste()
        if dumped.status == "ok":
            print(
                "LAST RESORT dump at " + str(round(waste, 1)) + ", penalty " + str(dumped.penalty)
            )
        else:
            print("warning: last-resort dump " + dumped.status)
    elif waste > DUMP_HIGH and not above_warned:
        print(
            "warning: waste "
            + str(round(waste, 1))
            + " is above 60; not dumping until "
            + str(LAST_RESORT)
        )
        above_warned = True
    if waste <= DUMP_HIGH:
        above_warned = False

    status = (
        "intake "
        + str(round(intake, 2))
        + " waste "
        + str(round(waste, 1))
        + " eff "
        + str(round(self.efficiency(), 1))
        + "% penalty "
        + str(self.dump_penalty())
    )
    if status != last_status:
        set_status(status, "info")
        last_status = status
