"""Probe: check the version call, component lookup and thermometer read.

Purpose: learn the runtime behaviour of three stub-declared calls. Each one has
a VERIFIED signature but UNVERIFIED behaviour.
Where it runs: attach to any machine script slot, or use Run Script in Game.
Read-only: changes no machine state and does not sleep or loop.
Inputs: none.
Assumptions: the thermometer machine exists in the save (it does in save_mvcjaxut_26ndfi).
API facts relied on: get_game_version, get_component, Thermometer.get_value (all
stub-declared, see docs/api-notes.md). Expected output is in docs/in-game-test-log.md (P-001).
"""

print("game version:", get_game_version())

thermometer = get_component("thermometer")
print("thermometer found:", thermometer is not None)

if thermometer is not None:
    print("type_id:", thermometer.type_id)
    print("surface temp (C):", thermometer.get_value())
