# Game reference (extracted from the in-game DOCS manual)

- Game build: `fe9a45c` (from the manual's header, "Build fe9a45c").
- Source: the owner's in-game DOCS manual, supplied as a Markdown export (about 41,000 lines). The full manual is split by section in `manual/` (local, git-ignored, ADR-023). Each file here is our own short extract, tagged **VERIFIED (docs)**.
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
| `harvester.md` | scanner and harvester: sectors, move, collect, heat |
| `biology.md` | Bio Collector, Bio Lab, Bio Exchange, first biology loop |
| `external-editor.md` | external editor: files, sync, collisions, console output |
| `contracts.md` | contracts, transmitter, contract statuses, shop and commander calls |
| `contracts-terminal-breach.md` | Alien Terminal Breach (`terminal_breach`): guess feedback, code length, answer format |
| `contracts-data-tablet.md` | Underground Data Tablet (`data_tablet`): probe, grid size, answer format |

## Not yet extracted

[manual/README.md](manual/README.md) indexes the whole manual by section. Read it for any area below, then add a short extract here when a script needs it.

Areas with no extract yet:

- Contract subtypes (14 left): per-contract APIs such as `LatticeGrid` and `Vault`.
- Numbers, strings and f-strings, lists, dicts, tuples, match/case, functions, generators, caching.
- Classes, dataclasses, enums, decorators, `@property`, operators in detail.
- Stdlib modules: `random`, `functools`, `re`, `dataclasses`, `enum`, `json`, `heapq`, `traceback`, `math`, `itertools`, `operator`, `string`, `collections`.
- Ship Computer, Shared Library, Automations, Data Archive, Signal Bus, Research.
- Machines: Oxygen Sensor, Thermometer, Pressure Sensor, Smelter, Refiner, terraforming machines, generators, Pioneer, Sonar, Drill, Nav, Clock, Console, Commander, Shop (entry), Earth Orders, Supply Dock, Map Markers, Flow networks, Weather, Habitat and wildlife.
- Code editor, debug mode, Vim mode, script variants and commands.
