"""Tests for probe_control_room: each check's verdict and console line, against fake panel and bus.

The fake panel records every widget call and can be told to fail one widget by name, the way the
game would raise a TypeError for a wrong argument shape. The loop is stopped after a fixed number of
clear() calls, so the tests see the first two passes (checks, then the persist row).
"""

from pathlib import Path
from types import SimpleNamespace

from tests.harness.fake_comms import FakeSignalBus
from tests.harness.fake_game import FakeGame
from tests.harness.loop import ScriptStop, run_loop

PROBE = Path(__file__).resolve().parent.parent / "scripts" / "probes" / "probe_control_room.py"


class FakePanel:
    def __init__(self, *, fail_widget=None, clicks=(), stop_after=2, mouse=(10, 20)):
        # Real mouse() returns a PanelMouse with x and y fields (stub: PanelMouse).
        self.fail_widget = fail_widget
        self.clicks_value = list(clicks)
        self.stop_after = stop_after
        self.mouse_value = mouse
        self.calls = []
        self.values = {}
        self.clears = 0

    def _record(self, name, *args):
        self.calls.append((name, args))
        if name == self.fail_widget:
            raise TypeError("wrong argument shape")

    def clear(self):
        self.clears += 1
        if self.clears > self.stop_after:
            raise ScriptStop

    def mouse(self):
        x, y = self.mouse_value
        return SimpleNamespace(x=x, y=y, over=False, pressed=False, released=False)

    def clicks(self):
        return list(self.clicks_value)

    def set_text(self, key, value):
        self.values[key] = value

    def get_text(self, key):
        return self.values.get(key)

    def set_switch(self, key, value):
        self.values[key] = value

    def get_switch(self, key):
        return self.values.get(key)

    def __getattr__(self, name):
        # Any drawing call is recorded and returns nothing, the way the game's draw calls do.
        if name.startswith("_"):
            raise AttributeError(name)

        def draw(*args, **_kwargs):
            self._record(name, *args)

        return draw


def _run(panel, *, bus=None):
    game = FakeGame()
    if bus is not None:
        game.components["comms"] = bus.as_component()
    run_loop(PROBE, game, owner=None, extra={"panel": panel})
    return game


def _console(game, name):
    return next(line for line in game.printed if line.startswith("probe " + name + ":"))


def test_widgets_draw_and_every_check_passes_on_a_working_fake():
    panel = FakePanel()
    game = _run(panel, bus=FakeSignalBus())

    assert _console(game, "widgets") == "probe widgets: PASS 12 widgets drawn\n"
    assert _console(game, "text") == "probe text: PASS round trip ok\n"
    assert _console(game, "switch") == "probe switch: PASS round trip ok\n"
    assert _console(game, "mouse") == "probe mouse: PASS x=10 y=20\n"
    assert _console(game, "bus") == "probe bus: PASS sizes 200, 2000, 20000 intact\n"


def test_persist_row_turns_pass_on_the_second_tick():
    game = _run(FakePanel(), bus=FakeSignalBus())

    assert "probe persist: WAIT next tick\n" in game.printed
    assert "probe persist: PASS counter kept between ticks\n" in game.printed


def test_a_failing_widget_is_named_in_the_widgets_row_and_others_still_draw():
    panel = FakePanel(fail_widget="combo")
    game = _run(panel, bus=FakeSignalBus())

    line = _console(game, "widgets")
    assert line.startswith("probe widgets: FAIL combo: wrong argument shape")
    # The check did not stop at the failing widget: a later one was still drawn.
    assert any(name == "draw_circle" for name, _ in panel.calls)


def test_bus_is_skipped_when_research_is_missing():
    game = _run(FakePanel(), bus=None)

    assert _console(game, "bus") == "probe bus: SKIP no Signal Bus: research not done\n"


def test_bus_check_fails_when_a_payload_comes_back_changed():
    bus = FakeSignalBus()
    original_send = bus.send

    def mangling_send(channel, value):
        value = dict(value, text=value["text"][:-1])
        return original_send(channel, value)

    bus.send = mangling_send
    game = _run(FakePanel(), bus=bus)

    assert _console(game, "bus") == "probe bus: FAIL payload 200 came back changed\n"


def test_click_row_waits_then_passes_once_a_click_is_seen():
    without = _run(FakePanel(), bus=FakeSignalBus())
    assert "probe click: WAIT click empty space on this card\n" in without.printed

    with_click = _run(FakePanel(clicks=[(5, 5)], stop_after=1), bus=FakeSignalBus())
    assert "probe click: PASS 1 click(s) seen\n" in with_click.printed


def test_text_check_reports_what_get_text_returned():
    panel = FakePanel()
    panel.get_text = lambda key: "wrong"
    game = _run(panel, bus=FakeSignalBus())

    assert _console(game, "text") == "probe text: FAIL get_text returned 'wrong'\n"


def test_bus_drains_its_channel_so_nothing_is_left_behind():
    bus = FakeSignalBus()
    _run(FakePanel(), bus=bus)

    assert bus.queues.get("ctrl.probe.echo", []) == []


def test_keyed_widgets_take_the_key_first_as_the_game_stub_does():
    # Run 1 in game failed on key order: the stub puts `key` first on these widgets.
    panel = FakePanel()
    _run(panel, bus=FakeSignalBus())

    keyed = {"button", "switch", "text_field", "combo"}
    for name, args in panel.calls:
        if name in keyed:
            assert isinstance(args[0], str), name
