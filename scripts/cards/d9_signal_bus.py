"""D9 Signal Bus monitor: the queued messages on one channel, and its latest broadcast.

Where it runs: Control Room card. Works at any size; rows that do not fit are counted, not drawn.
    Paste this file as the card's script (Control Room > + New Card). Not synced: paste it in game,
    like the Automations. This is the debug view for the control cards: type a channel name into
    the field.
Inputs: the channel name, typed into the text field on the card. Reads comms.pending and
    comms.latest_info only; it sends and receives nothing.
Assumptions: Library `control_room` is in game lib/ (synced from scripts/libs/, owner go-ahead).
API facts relied on (VERIFIED stub): get_component("comms") (None until Signal Bus research),
    pending(channel), latest_info(channel) (BroadcastInfo: value, sender); CommsMessage fields id,
    sender, tick, value; panel.text_field, draw_text, card.
"""

from control_room import fit_text, format_message, rows_for, valid_channel

DEFAULT_CHANNEL = "ctrl.rover_1.dispatch"
CHANNEL_KEY = "bus.channel"
MARGIN = 16
FIRST_ROW_Y = 96
ROW_HEIGHT = 18
BOTTOM_PAD = 24
LATEST_X = 150


def draw_pending(comms, channel, width, height):
    content = width - 2 * MARGIN
    messages = comms.pending(channel)
    panel.draw_text(MARGIN, 80, str(len(messages)) + " pending", 12, "text-secondary")
    visible = rows_for(height, FIRST_ROW_Y, ROW_HEIGHT, BOTTOM_PAD)
    for index, message in enumerate(messages[:visible]):
        line = format_message(message.id, message.sender, message.tick, message.value)
        panel.draw_text(
            MARGIN, FIRST_ROW_Y + index * ROW_HEIGHT, fit_text(line, content, 12), 12, "text-bright"
        )
    hidden = len(messages) - visible
    if hidden > 0:
        panel.draw_text(MARGIN, height - 12, "+" + str(hidden) + " more", 11, "text-muted")


def draw_latest(comms, channel, width):
    info = comms.latest_info(channel)
    text = "no broadcast on this channel" if info is None else "broadcast: " + str(info.value)
    panel.draw_text(
        MARGIN + LATEST_X, 80, fit_text(text, width - 2 * MARGIN - LATEST_X, 12), 12, "text-value"
    )


while True:
    panel.clear()
    width = panel.width()
    height = panel.height()
    panel.card(4, 4, width - 8, height - 8, "SIGNAL BUS")
    content = width - 2 * MARGIN
    channel = panel.text_field(
        CHANNEL_KEY, MARGIN, 36, min(360, content), DEFAULT_CHANNEL, "channel name", "Channel"
    )
    if not valid_channel(channel):
        hint = "Use letters, digits, _ . : - (1-64 characters)"
        panel.draw_text(MARGIN, 60, fit_text(hint, content, 11), 11, "error")
    else:
        comms = get_component("comms")
        if comms is None:
            panel.draw_text(MARGIN, 80, "Signal Bus not researched yet", 13, "text-muted")
        else:
            draw_pending(comms, channel, width, height)
            draw_latest(comms, channel, width)
