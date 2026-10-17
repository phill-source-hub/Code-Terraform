"""Adapter tests: the o2gen_1 script against a fake generator and atmosphere."""

from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_game import FakeComponent, FakeGame, run_script

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "main" / "o2gen_1.py"


class _Stop(Exception):
    """Ends the generator's endless loop after one pass."""


class StopOnSleep(FakeGame):
    def sleep(self, seconds: float, /) -> None:
        super().sleep(seconds)
        raise _Stop


def generator(waste=30.0, co2=800.0, intake_status="ok", dump_status="ok", penalty=0.0):
    record: list = []
    gen = SimpleNamespace(
        set_intake=lambda value: (
            record.append(("set_intake", value))
            or SimpleNamespace(status=intake_status, message="")
        ),
        waste=lambda: waste,
        dump_waste=lambda: (
            record.append(("dump",))
            or SimpleNamespace(status=dump_status, message="", penalty=penalty)
        ),
        dump_penalty=lambda: penalty,
        efficiency=lambda: 100.0,
    )
    return gen, record, co2


def run(gen, co2, atmosphere=True, seconds=60.0):
    game = StopOnSleep()
    if atmosphere:
        game.components["atmosphere"] = FakeComponent(
            id="atmosphere",
            type_id="atmosphere",
            methods={"get_co2": lambda: co2},
        )
    game.components["clock"] = FakeComponent(
        id="clock", type_id="clock", methods={"real_seconds_per_hour": lambda: seconds * 60}
    )
    with suppress(_Stop):
        run_script(
            SCRIPT.read_text(encoding="utf-8"),
            game,
            filename=str(SCRIPT),
            extra_globals={"self": gen},
        )
    return game


def test_sets_intake_to_one_tenth_of_co2():
    gen, record, co2 = generator(waste=10.0, co2=800.0)
    run(gen, co2)
    assert ("set_intake", 80.0) in record


def test_does_not_dump_below_the_dump_threshold():
    gen, record, co2 = generator(waste=30.0)
    run(gen, co2)
    assert ("dump",) not in record


def test_dumps_at_fifty_so_the_dump_lands_in_the_clean_window():
    gen, record, co2 = generator(waste=52.0, penalty=0.0)
    game = run(gen, co2)
    assert ("dump",) in record
    assert any("dumped waste at 52.0, penalty 0.0" in line for line in game.printed)


def test_dumps_even_above_sixty_to_avoid_the_stall():
    gen, record, co2 = generator(waste=72.0, penalty=0.25)
    game = run(gen, co2)
    assert ("dump",) in record
    assert any("penalty 0.25" in line for line in game.printed)


def test_rejected_intake_is_printed_as_a_warning():
    gen, record, co2 = generator(intake_status="offline")
    game = run(gen, co2)
    assert "warning: set_intake offline\n" in game.printed


def test_rejected_dump_is_printed_as_a_warning():
    gen, record, co2 = generator(waste=55.0, dump_status="busy")
    game = run(gen, co2)
    assert "warning: dump busy\n" in game.printed


def test_status_shows_intake_waste_efficiency_and_penalty():
    gen, record, co2 = generator(waste=30.0, penalty=0.0)
    game = run(gen, co2)
    assert game.statuses[-1] == ("intake 80.0 waste 30.0 eff 100.0% penalty 0.0", "info")


def test_missing_atmosphere_is_an_error_and_nothing_is_set():
    gen, record, co2 = generator()
    game = run(gen, co2, atmosphere=False)
    assert game.statuses[-1] == ("atmosphere not found", "error")
    assert record == []


def test_paces_one_pass_per_sixtieth_of_a_world_hour():
    gen, record, co2 = generator()
    game = run(gen, co2, seconds=60.0)
    assert game.clock.now == 60.0


def test_machine_script_has_no_imports():
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        assert not line.strip().startswith(("import ", "from ")), line
