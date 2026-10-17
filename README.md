# Code-Terraform

Scripts for the game **Code: Terraform** (Steam 868160, by AppsMafia). The game runs its own Python-like language, not CPython, so this repo has a test harness that fakes the in-game API.

## Set up the game's External Editor

1. In the game: Settings > Editor > External Editor > **Set Up VS Code** (or PyCharm / Zed, see the game's `CODE-TERRAFORM-IDE.txt`).
2. The game keeps its own scripts folder at `%APPDATA%\io.codeterraform.game\save_mvcjaxut_26ndfi_scripts` (this save). That folder holds generated files, saves and logs. It is **not** this repo.
3. Scripts in this repo are copied into that folder by a sync step. The sync step is not written yet and needs your approval before it touches the game folder.

## Set up this repo

Requires Windows PowerShell or PowerShell 7, Python 3.12 and git.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
git config core.hooksPath .githooks   # enables the pre-commit check, once per clone
```

## Run the checks

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 check    # format + lint + tests
powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 test     # tests only
powershell -NoProfile -ExecutionPolicy Bypass -File tasks.ps1 format   # apply formatting
```

CI runs `check` on every push and pull request (`.github/workflows/ci.yml`).

## Layout

| Path | Contents |
|------|----------|
| `scripts/main/` | per-machine programs (file name = machine id) |
| `scripts/libs/` | shared Libraries (game `lib/`) |
| `scripts/probes/` | probe scripts that check UNVERIFIED API facts |
| `tests/` | pytest suite; `tests/harness/` is the fake game API |
| `docs/` | `api-notes.md`, `decisions.md`, `in-game-test-log.md` |
| `.claude/agents/` | Claude Code subagents used for this project |

## Script index

| Name | Purpose | Where it runs | Status |
|------|---------|---------------|--------|
| (none yet) | | | |

Status values: Draft, L1+L2 pass, L3 pending, Done.

## Limits

- Game API facts are tagged VERIFIED or UNVERIFIED in `docs/api-notes.md`. Only stub-declared shapes are VERIFIED so far; behaviour is UNVERIFIED until checked in game.
- Tests run under CPython against a fake. Passing tests do not prove the game behaves the same; the in-game checklist does that.

## License

GPL-3.0. See [LICENSE](LICENSE).
