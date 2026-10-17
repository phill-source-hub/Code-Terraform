# External Editor: files, sync and collisions

Source: in-game DOCS manual, build `fe9a45c`, sections "External Editor", "When edits collide", "Console output in your editor". Tag: **VERIFIED (docs)**. Short notes in our own words.

## Live sync

- Edits in game are written to disk within about half a second.
- Edits on disk are picked up by the game within about 250 ms. The in-game buffer refreshes.
- If the OS cannot watch the folder, the game rescans every 2 s and logs that once.
- A file another program is holding is retried briefly before the game gives up.

## Files in the scripts folder

- `<name>.py`: one per machine, panel or contract script. Contract scripts sit at the root too, named by their contract id (for example `relay_hack.py`).
- `lib/<name>.py`: Library scripts. Import as `from <name> import ...`.
- `user_stubs.py`: owner's type declarations. Never overwritten. No executable helpers.
- `logs/all.log` and one log per script. Rotated by size.
- Do not edit: `codeterraform-workspace.json`, `codeterraform-scripts.json`, `codeterraform-fleet.json`.
- Generated, safe to ignore: `*.pyi`, `pyrightconfig.codeterraform.json`, `.codeterraform/`.
- Recovery files: `*.codeterraform-retired-<token>.bak`. The game keeps one when a file is renamed, deleted, replaced or in conflict. Safe to delete.
- Variants and Notes tabs live in the save, not in this folder.

## Library changes need Apply

- Saved Library edits do not apply on save.
- Apply (in game, or Apply Library in Game in VS Code) deploys them and restarts scripts that import them.
- Our sync tool copies Library files only. After a Library change, Apply in game.

## Collisions

- If a file changes on disk while you edit it in game, nothing is replaced and nothing is locked.
- The in-game editor shows a bar. Options: Keep mine (write your version to the file), Use other version (switch to disk), Merge both, Compare.
- If no copy of the other version could be saved yet, the game leaves the file alone. Save a copy again, or Overwrite the file.

## What our tooling does with this

- `tools/sync_to_game.py` refuses to overwrite a file that changed in game since our last write (a conflict). Same idea as the game's collision bar.
- Exception: a file whose only content is `Help me` on line 1 is an owner request and may be replaced. See ADR-012.
- `tasks.ps1 pull` copies game-side edits to `.sync-pull/` for review. It never writes into the repo.
- `tasks.ps1 status` reads `logs/all.log` for warnings and errors.

## Editor setup (for reference)

- VS Code: External Editor > Set Up VS Code. Language server is installed by the game. No Python needed.
- Other editors: `node <app-data>/external-ide/server/server.cjs --stdio`, scripts folder as the workspace root.
- Debugging: F5 in VS Code attaches to a running script. Breakpoints use the game's interpreter. Watches are read-only.
