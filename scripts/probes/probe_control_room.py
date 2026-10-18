"""Probe: Control Room panel API and Signal Bus payload. Step 0 of docs/specs/control-room-cards.md.

Where it runs: a Control Room card. Open the Control Room, click + New Card, paste this file as the
    card's script. Use a 2x1 card so the rows fit. Delete the card when the probe is done.
Inputs: one click on empty space on the card (checks clicks()). Nothing else is needed.
Assumptions: argument shapes follow the game stub (`__builtins__.pyi`, VERIFIED stub). Behaviour is
    not verified until the in-game log passes. A FAIL that says TypeError means the stub and the
    call disagree: fix the call.
Run 1 (2026-10-18, panel_1.py): widgets FAILed on key order (key goes first); bus FAILed because
    the packet is a CommsMessage, so the check compares .value, not str(packet).
Checks run once, on the first pass, and their results are kept in module state and drawn each tick:
    widgets  each named widget and primitive is drawn without error
    persist  module state survives between ticks (row turns PASS on the second tick)
    text     set_text / get_text round trip
    switch   set_switch / get_switch round trip
    mouse    mouse() returns a value
    click    clicks() reports a click on empty card space (WAIT until you click)
    bus      comms send / receive at payload sizes 200, 2000 and 20000 characters
Console: one line per check, "probe <name>: PASS|FAIL|SKIP|WAIT <detail>", printed when it is set.
Safety: no machine is commanded. The bus check sends only to ctrl.probe.echo and drains that channel
    at the end, bounded by DRAIN_LIMIT.
API facts relied on (all UNVERIFIED until the in-game log passes): panel.clear, draw_text, label,
    status_dot, progress_bar, button, switch, text_field, combo, card, draw_rect, draw_line,
    draw_circle, set_text, get_text, set_switch, get_switch, mouse, clicks; get_component("comms")
    with send, receive; print. Log results in docs/in-game-test-log.md (row PX-001).
"""

PAYLOAD_SIZES = (200, 2000, 20000)
CHANNEL = "ctrl.probe.echo"
# A probe loop still needs a bound, same rule as every loop in this repo.
DRAIN_LIMIT = 50
ORDER = ("widgets", "persist", "text", "switch", "mouse", "click", "bus")
ROW_STATE = {"PASS": "running", "FAIL": "error", "SKIP": "idle", "WAIT": "idle"}


def _widget_calls():
    # Built per call so a missing name fails inside check_widgets, not at paste time.
    return [
        ("card", lambda: panel.card(4, 4, 400, 190, "probe")),
        ("draw_text", lambda: panel.draw_text(10, 20, "probe", 12)),
        ("label", lambda: panel.label(10, 40, "PROBE", "caption")),
        ("status_dot", lambda: panel.status_dot(10, 60, 5, "running")),
        ("progress_bar", lambda: panel.progress_bar(60, 54, 80, 10, 0.5, "success")),
        ("button", lambda: panel.button("probe.button", 160, 50, 80, 20, "Probe")),
        ("switch", lambda: panel.switch("probe.switch", 260, 50)),
        ("text_field", lambda: panel.text_field("probe.text", 10, 90, 200)),
        ("combo", lambda: panel.combo("probe.combo", 230, 90, 120, ["a", "b"])),
        ("draw_rect", lambda: panel.draw_rect(10, 130, 40, 20, "border")),
        ("draw_line", lambda: panel.draw_line(60, 130, 120, 150, "accent")),
        ("draw_circle", lambda: panel.draw_circle(140, 140, 6, "accent")),
    ]


def check_widgets():
    failed = []
    calls = _widget_calls()
    for name, call in calls:
        try:
            call()
        except Exception as error:
            # The probe is a boundary: record every failure, including the game's own
            # TypeError for a wrong argument shape, and carry on to the next widget.
            failed.append(name + ": " + str(error))
    if failed:
        return "FAIL", "; ".join(failed)[:200]
    return "PASS", str(len(calls)) + " widgets drawn"


def check_text():
    panel.set_text("probe.text", "abc")
    value = panel.get_text("probe.text")
    if value == "abc":
        return "PASS", "round trip ok"
    return "FAIL", "get_text returned " + repr(value)


def check_switch():
    panel.set_switch("probe.switch", True)
    value = panel.get_switch("probe.switch")
    if value is True:
        return "PASS", "round trip ok"
    return "FAIL", "get_switch returned " + repr(value)


def check_mouse():
    position = panel.mouse()
    if position is None:
        return "FAIL", "mouse() returned None"
    return "PASS", "x=" + str(position.x) + " y=" + str(position.y)


def check_bus(comms):
    if comms is None:
        return "SKIP", "no Signal Bus: research not done"
    sizes = []
    for size in PAYLOAD_SIZES:
        text = "x" * size
        sent = comms.send(CHANNEL, {"req": size, "text": text})
        if sent.status != "ok":
            return "FAIL", "send " + str(size) + ": " + sent.status + " " + sent.message
        got = comms.receive(CHANNEL, sent.message_id)
        if got.status != "ok":
            return "FAIL", "receive " + str(size) + ": " + got.status
        # The packet is a CommsMessage; the sent dict is on its .value field.
        if got.packet.value != {"req": size, "text": text}:
            return "FAIL", "payload " + str(size) + " came back changed"
        sizes.append(str(size))
    _drain(comms)
    return "PASS", "sizes " + ", ".join(sizes) + " intact"


def _drain(comms):
    for _ in range(DRAIN_LIMIT):
        if comms.receive(CHANNEL).status != "ok":
            return


def _run_once(rows):
    rows["widgets"] = check_widgets()
    rows["text"] = check_text()
    rows["switch"] = check_switch()
    rows["mouse"] = check_mouse()
    rows["bus"] = check_bus(get_component("comms"))
    rows["persist"] = ("WAIT", "next tick")
    rows["click"] = ("WAIT", "click empty space on this card")
    for name in ORDER:
        outcome, detail = rows[name]
        print("probe " + name + ": " + outcome + " " + detail)


def _draw(rows, ticks):
    panel.draw_text(300, 20, "tick " + str(ticks), 11)
    y = 150
    for name in ORDER:
        outcome, detail = rows[name]
        panel.status_dot(20, y, 5, ROW_STATE[outcome])
        panel.draw_text(34, y, name + " " + outcome + " " + detail[:60], 12)
        y += 16


rows = {}
ticks = 0
while True:
    ticks += 1
    panel.clear()
    if ticks == 1:
        _run_once(rows)
    if ticks == 2:
        rows["persist"] = ("PASS", "counter kept between ticks")
        print("probe persist: PASS counter kept between ticks")
    clicks = panel.clicks()
    if clicks and rows["click"][0] == "WAIT":
        rows["click"] = ("PASS", str(len(clicks)) + " click(s) seen")
        print("probe click: PASS " + rows["click"][1])
    _draw(rows, ticks)
