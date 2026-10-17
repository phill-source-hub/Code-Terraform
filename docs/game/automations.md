# Automations

Source: in-game DOCS manual, build `fe9a45c`. Section: "Automations" (manual `56-automations.md`). Tag: **VERIFIED (docs)**. Short notes, own words.

## What it is

- An automation is a script that belongs to no machine. It is for work across the whole base: power, shop, deployment, construction planning.
- Unlock: **Automations** research. Create it from **Ship Computer > Automations > + New Automation**.
- Our repo copy: `scripts/automations/<name>.py`. Not synced by `tools/sync_to_game.py`; paste it into the game (see README).

## How it runs

- It runs whichever page is open. It has no power supply, so a brownout does not pause it.
- It restarts with the game like any other running script. Start, stop and edit it from the Automations tab, the Scripts tab, or its editor window.

## What it can and cannot do

- Reads every component through `get_component()`.
- Can give orders to shared systems that take orders from any script, such as `power_control`, `run_control`, `shop`, `inventory`, `computer`, `comms`.
- There is **no `self`**. A machine's own actions (moving a vehicle, mining, setting a recipe) work only from that machine's script. To make a machine act, send it a message on the Signal Bus.

## Limits

- 50 automations per save.
- One script per automation. For separate jobs, make separate automations.
- Deleting an automation keeps its code under **Computer > Scripts > Unassigned**.

## Notes for our scripts

- Library imports (docs/game/libraries.md) are documented for scripts in general. The manual's Automations section does not say whether an automation can import. **UNVERIFIED for automations**: check in game with the base watch checklist before relying on it.
- Keep loops paced with `sleep()`, as for machine scripts (CLAUDE.md).
