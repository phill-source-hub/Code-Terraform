"""Fake Control Room panel for card tests: records every call and answers the input widgets.

Draw calls are recorded as (name, args, kwargs) and returned as nothing, as the game's draw calls
are. Input widgets return a stored value when the test set one, else the default the card passed,
the way a player who has not touched them would leave them. The script is stopped after
`stop_after` clear() calls, one clear per tick, so a test sees a fixed number of passes.
"""

from tests.harness.loop import ScriptStop


class FakePanel:
    def __init__(self, *, width=1000, height=200, stop_after=1, mouse=(0, 0), clicks=()):
        self._width = width
        self._height = height
        self._stop_after = stop_after
        self._mouse = mouse
        self._clicks = list(clicks)
        self.calls = []
        self.values = {}
        self.clears = 0

    def clear(self):
        self.clears += 1
        if self.clears > self._stop_after:
            raise ScriptStop

    def width(self):
        return self._width

    def height(self):
        return self._height

    def mouse(self):
        return self._mouse

    def clicks(self):
        return list(self._clicks)

    def text_field(self, key, x, y, w, default="", *args, **kwargs):
        self.calls.append(("text_field", (key, x, y, w), {}))
        return self.values.get(key, default)

    def combo(self, key, x, y, w, options, default=None, *args, **kwargs):
        self.calls.append(("combo", (key, x, y, w, options), {}))
        return self.values.get(key, default)

    def button(self, key, x, y, w=0, h=0, label="", *args, **kwargs):
        self.calls.append(("button", (key, x, y, w, h, label), {}))
        return False

    def switch(self, key, x, y, default_on=False, *args, **kwargs):
        self.calls.append(("switch", (key, x, y), {}))
        return self.values.get(key, default_on)

    def set_text(self, key, text):
        self.values[key] = text

    def get_text(self, key):
        return self.values.get(key)

    def set_switch(self, key, on):
        self.values[key] = on

    def get_switch(self, key):
        return self.values.get(key)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def draw(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return draw

    def named(self, name):
        """The argument tuples of every call to `name`, in order."""
        return [args for call_name, args, _ in self.calls if call_name == name]

    def texts(self):
        """Every string the card drew with draw_text, in order."""
        return [args[2] for args in self.named("draw_text")]
