"""Oxygen generator controller: CO2 intake at peak, waste dumped before it costs efficiency.

Where it runs: machine script slot `o2gen_1` (self = this generator). Mk I.
Self-contained on purpose (ADR-014): no imports.
Rules (manual, Oxygen Generator and Atmosphere):
    peak intake is CO2 / 10 (ppt); waste is clean up to 60, falls off from 60, stalls at 100;
    dumping between 50 and 60 is penalty-free; intake returns to 0 when this script stops.
Policy, each pass:
    1. set intake to CO2 / 10 from get_component("atmosphere").get_co2();
    2. dump as soon as waste reaches DUMP_FROM (50), so the dump lands in the clean window.
       If waste has already passed 60, dump anyway: a penalty is better than the stall at 100.
Pacing: one pass per 1/60 world-clock hour, the same as the solar tracker.
Failure: a missing atmosphere or a rejected call is shown as a warning or error. The loop goes on.
API facts relied on (docs/game/power.md is the solar pattern; oxygen rules from the manual):
    self.set_intake(value), self.waste(), self.dump_waste() (.status, .penalty),
    self.dump_penalty(), self.efficiency(), get_component("atmosphere").get_co2(),
    get_component("clock").real_seconds_per_hour(), set_status, print, sleep.
"""

DUMP_FROM = 50
PASSES_PER_WORLD_HOUR = 60

atmosphere = get_component("atmosphere")
clock = get_component("clock")
period = 60.0
if clock is not None:
    period = clock.real_seconds_per_hour() / PASSES_PER_WORLD_HOUR

while True:
    if atmosphere is None:
        set_status("atmosphere not found", "error")
        sleep(period)
        continue

    co2 = atmosphere.get_co2()
    intake = co2 / 10
    setting = self.set_intake(intake)
    if setting.status != "ok":
        print("warning: set_intake " + setting.status)

    waste = self.waste()
    if waste >= DUMP_FROM:
        dumped = self.dump_waste()
        if dumped.status == "ok":
            print("dumped waste at " + str(round(waste, 1)) + ", penalty " + str(dumped.penalty))
        else:
            print("warning: dump " + dumped.status)

    set_status(
        "intake "
        + str(round(intake, 1))
        + " waste "
        + str(round(waste, 1))
        + " eff "
        + str(round(self.efficiency(), 1))
        + "%"
        + " penalty "
        + str(self.dump_penalty()),
        "info",
    )
    sleep(period)
