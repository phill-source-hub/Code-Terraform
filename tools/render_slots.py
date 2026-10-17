"""Write one machine script per slot from its shared template.

Where it runs: on the dev machine, outside the game. Never runs game code.
Inputs: `scripts/templates/*.py`, each with the token `__SLOT__` where the slot name goes.
Outputs: `scripts/main/<slot>.py`, one per entry in SLOTS.
Why: the game needs a separate file per machine slot, but two slots running the same controller
    must not drift apart. One template is the source; each slot file is generated from it.
Commands: `python tools/render_slots.py` writes the files; `--check` writes nothing and exits 1
    if a committed slot file no longer matches its template (the test suite runs the same check).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "scripts" / "templates"
MAIN = ROOT / "scripts" / "main"
TOKEN = "__SLOT__"

# Slot ids as the game names machine slots: lower case, underscore, number (e.g. solar_2).
SLOT_PATTERN = re.compile(r"^[a-z][a-z0-9]*_[0-9]+$")

# Which template each machine slot is generated from.
SLOTS = {
    "solar_1": "solar_slot.py",
    "solar_2": "solar_slot.py",
    "solar_3": "solar_slot.py",
    "pressure_1": "pressure_slot.py",
    "pressure_2": "pressure_slot.py",
    "pressure_3": "pressure_slot.py",
    "o2gen_1": "o2gen_slot.py",
    "o2gen_2": "o2gen_slot.py",
    "o2gen_3": "o2gen_slot.py",
}


def render(template: str, slot: str) -> str:
    """Template text with every slot token replaced by the slot name."""
    if not SLOT_PATTERN.match(slot):
        raise ValueError(f"not a machine slot id: {slot!r}")
    return template.replace(TOKEN, slot)


def expected_files(templates: Path = TEMPLATES) -> dict[Path, str]:
    """Each generated file's path mapped to the text it must contain."""
    files: dict[Path, str] = {}
    for slot, template_name in sorted(SLOTS.items()):
        template = (templates / template_name).read_text(encoding="utf-8")
        files[MAIN / f"{slot}.py"] = render(template, slot)
    return files


def drifted(files: dict[Path, str]) -> list[Path]:
    """Generated files that are missing or differ from what the template now produces."""
    stale = []
    for path, text in files.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            stale.append(path)
    return stale


def _label(path: Path) -> str:
    # Repo-relative for readable output; a path outside the repo (e.g. a test's temp dir) as is.
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report drift; write nothing")
    args = parser.parse_args(argv)
    files = expected_files()
    if args.check:
        stale = drifted(files)
        for path in stale:
            print(f"out of date: {_label(path)}")
        return 1 if stale else 0
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {_label(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
