import pytest

from tests.harness.fake_game import FakeComponent, FakeGame, run_script


def test_print_is_captured_with_sep_and_end():
    game = FakeGame()
    run_script("print('a', 1, sep='|')\nprint('b')\n", game)
    assert game.printed == ["a|1\n", "b\n"]


def test_sleep_advances_fake_clock_without_blocking():
    game = FakeGame()
    run_script("sleep(2.5)\n", game)
    assert game.clock.now == 2.5


def test_negative_sleep_is_rejected_by_fake_clock():
    game = FakeGame()
    with pytest.raises(ValueError):
        run_script("sleep(-1)\n", game)


def test_unknown_game_name_fails_loudly_as_name_error():
    # A script calling an API we have not faked must fail, not silently pass.
    game = FakeGame()
    with pytest.raises(NameError, match="activate_power"):
        run_script("activate_power()\n", game)


def test_cpython_only_builtin_is_not_visible():
    # The game's builtin list is curated; `open` must not leak in from CPython.
    game = FakeGame()
    with pytest.raises(NameError, match="open"):
        run_script("open('x')\n", game)


def test_get_component_returns_none_for_unknown_machine():
    game = FakeGame()
    ns = run_script("found = get_component('nope')\n", game)
    assert ns["found"] is None


def test_get_component_returns_registered_machine():
    game = FakeGame()
    thermo = FakeComponent(
        id="thermometer", type_id="thermometer", methods={"get_value": lambda: 21.5}
    )
    game.components["thermometer"] = thermo
    ns = run_script("t = get_component('thermometer')\nvalue = t.get_value()\n", game)
    assert ns["value"] == 21.5


def test_missing_component_method_raises_attribute_error():
    component = FakeComponent(id="thermometer", type_id="thermometer")
    with pytest.raises(AttributeError, match="get_value"):
        _ = component.get_value


def test_notify_accepts_duration_and_dismissible_keywords():
    # Stub signature: notify(text, /, level, duration_seconds, dismissible).
    game = FakeGame()
    run_script("notify('boom', level='error', duration_seconds=0)\n", game)
    assert game.notifications == [("boom", "error")]


def test_set_status_records_message_and_level():
    game = FakeGame()
    run_script("set_status('ok', 'info')\n", game)
    assert game.statuses == [("ok", "info")]
