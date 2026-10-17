# Game reference (extracted from the in-game DOCS manual)

- Game build: `fe9a45c` (from the manual's header, "Build fe9a45c").
- Source: the owner's copy of the in-game DOCS manual, supplied as a Markdown export (about 41,000 lines). Not copied wholesale. Each file here is our own short extract, tagged **VERIFIED (docs)**.
- To refresh: read the matching section in the manual and update the file. Bump the build id above.

## Files

| File | Covers |
|------|--------|
| `language.md` | output, self and components, command results, long-running scripts, exceptions, loops, docstrings |
| `libraries.md` | imports, Libraries, built-in modules, typing-only names |
| `rover.md` | Rover: properties, nav, sonar, drill, input and output, mount and unmount, status |
| `power.md` | power grids, power control, batteries, battery charger, solar generator, vehicle charging and swaps |
| `fabricator.md` | fabricator, sample recipes, item ports, transfer results, ItemStack |
| `drone.md` | drones, fleet, drone service station, weather collection |
| `contracts.md` | contracts, transmitter, contract statuses, shop and commander calls |
| `contracts-terminal-breach.md` | Alien Terminal Breach (`terminal_breach`): guess feedback, code length, answer format |
| `contracts-data-tablet.md` | Underground Data Tablet (`data_tablet`): probe, grid size, answer format |

## Not yet extracted

Add a file when a script needs it:

- Contract subtypes (14 left): per-contract APIs such as `LatticeGrid`, `Vault`.
- Numbers, strings and f-strings, lists, dicts, tuples, match/case, functions, generators, caching.
- Classes, dataclasses, enums, decorators, `@property`, operators in detail.
- Stdlib modules: `random`, `functools`, `re`, `dataclasses`, `enum`, `json`, `heapq`, `traceback`, `math`, `itertools`, `operator`, `string`, `collections`.
- Machine references not yet covered: Scanner, Harvester, Oxygen Sensor, Thermometer, Pressure Sensor, Bio machines, Smelter, Refiner, Terraforming machines, Heat, Oxygen and Pressure Generators, Vehicle Charging Station (entry), Pioneer, Sonar Module, Drill Module, Nav Module, Data Archive, Signal Bus, Run Control, Clock, Console, Commander, Shop (entry), Research, Earth Orders, Supply Dock, Map Markers, Automations, Flow networks and pipes, Weather, Habitat and wildlife.
- Code editor, debug mode, Vim mode, script variants and commands.
