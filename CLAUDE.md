# Code-Terraform: project memory

Scripting repo for the game Code: Terraform (Steam 868160, AppsMafia). Pet project, but keep it clean, tested and version-controlled. Global rules in `C:\Users\Phill\.claude\CLAUDE.md` also apply.

## Ground truth rules (non-negotiable)

- The game language is Python-like, NOT Python, and runs only in the game. Never assume a builtin, module or API exists.
- Tag every API fact in `docs/api-notes.md` as VERIFIED (stub, ingame) or UNVERIFIED. Write code only on VERIFIED facts, unless the owner approves a probe.
- Only `linted` is not `tested`. Anything the game must show is checked in game via `docs/in-game-test-log.md`.
- Do not copy game assets or docs wholesale into committed files. Notes are short, in our own words. The owner's full manual is a git-ignored local copy in `docs/game/manual/` (ADR-023): never commit it or push it.
- Never write to the game folder (`%APPDATA%\io.codeterraform.game\save_mvcjaxut_26ndfi_scripts`) or any path outside this repo without asking.
- The game folder holds generated files (stubs, workspace, logs, saves). Leave them alone.

## Game docs

- Extracts from the in-game DOCS manual (build `fe9a45c`) live in `docs/game/`. Index: `docs/game/README.md`. The full manual, split by section, is in `docs/game/manual/` (local only).
- Facts from those files are VERIFIED (docs). Stub-only facts are VERIFIED (stub). Everything else is UNVERIFIED.
- Loops: the game yields during `while` loops by itself, but use `sleep()` to pace polling. Every loop still needs a bound or a sleep.

## Game folder: owner go-ahead before writes

- The in-game tutorial is complete (2026-10-17, ADR-011). Each `tools/sync_to_game.py apply` still needs the owner's go-ahead. Writes go only to the game folder (`%APPDATA%\io.codeterraform.game\save_mvcjaxut_26ndfi_scripts`).
- `tasks.ps1 sync` is a dry run. `tasks.ps1 status` is read-only (logs and script status). Use `status` to check errors.
- `tools/sync_to_game.py apply` writes only the files we own. Conflicts are refused, never overwritten.

## Layout

- `scripts/main/` per-machine programs, file named as the machine id (game root `<id>.py`).
- `scripts/libs/` shared Libraries (game `lib/<name>.py`).
- `scripts/templates/` shared controllers with a `__SLOT__` token; `tools/render_slots.py` generates `scripts/main/<slot>.py` (ADR-027). Edit the template, never the generated file.
- `scripts/probes/` one-off probe scripts for UNVERIFIED facts.
- `scripts/contracts/` contract scripts (game root). `scripts/automations/` Automations (game Ship Computer > Automations), not synced: paste them in game (README).
- `docs/specs/` feature specs. `docs/game/manual/` local manual copy (git-ignored).
- `tests/` pytest; `tests/harness/fake_game.py` is the fake game API.
- `docs/` `api-notes.md`, `decisions.md` (ADRs), `in-game-test-log.md`.
- `.claude/agents/` ct-scripter, ct-tester, ct-reviewer, ct-docs.
- `.githooks/pre-commit` runs `check`. `.github/workflows/ci.yml` runs `check` on push and PR.

## Commands

- `powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 check` format check + lint + tests (the gate).
- `... tasks.ps1 test` pytest only. `... tasks.ps1 lint`. `... tasks.ps1 format` applies ruff format.
- Tools are pinned in `requirements-dev.txt`; install into `.venv` only.
- No `make` on this machine; `tasks.ps1` is the runner.

## Conventions

- Python 3.12 style, ruff-formatted, line length 100, double quotes (`ruff.toml`).
- Game code is pure logic + thin adapter. Logic has no game calls; adapter calls only VERIFIED names.
- Each script starts with a docstring: purpose, where it runs, inputs, assumptions, API facts relied on.
- Comment why, not what.
- Commits: Conventional Commits (`feat(scope):`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`). Small and scoped.

## Workflow

1. Spec (5-10 lines) with goal, machine, inputs, success criteria, safety limits.
2. Branch `feat/<name>` or `fix/<name>`. Never commit to `main`.
3. ct-tester: tests + in-game checklist. ct-scripter: implementation. Run `check`.
4. ct-reviewer: review. Fix blocking items.
5. ct-docs: README index, api-notes, decisions.
6. Commit locally in small steps. Push and PR only after owner says so. Owner merges. Never force-push, rewrite history or delete branches without explicit OK.

## Safety

- Drones, rovers and machines: every loop bounded; check battery, oil, power before moving; never assume a call succeeded (check the status literal).
- No secrets, saves, personal logs or `.env` in git. `.gitignore` covers them.

## API notes policy

- `docs/api-notes.md` is the only source of API facts for code.
- A fact moves to VERIFIED only with evidence: a stub line, a pasted in-game doc, or a passed in-game checklist row.
- After a game update, stale facts get flagged, not silently kept.

## Known gaps

- Behaviour docs: the full manual is in `docs/game/manual/` (local). Our extracts in `docs/game/` cover only some areas, so check the manual before writing code for an area not extracted.
- Game-vs-Ruff syntax differences: one logged in `docs/api-notes.md` (the `/=` report). Log more there as found.
