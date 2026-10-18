"""D9 Signal Bus monitor: the queued messages on one channel, and its latest broadcast.

Where it runs: Control Room card, size 2x1 (1000 x 200). Paste this file as the card's script
    (Control Room > + New Card). Not synced: paste it in game, like the Automations.
    This is the debug view for the control cards: type a channel name into the field.
Inputs: the channel name, typed into the text field on the card. Reads comms.pending and
    comms.latest_info only; it sends and receives nothing.
Assumptions: Library `control_room` is in game lib/ (synced from scripts/libs/, owner go-ahead).
API facts relied on (VERIFIED stub): get_component("comms") (None until Signal Bus research),
    pending(channel), latest_info(channel) (BroadcastInfo: value, sender); CommsMessage fields id,
    sender, tick, value; panel.text_field, draw_text, card.
"""

from control_room import format_message, short_text, valid_channel

DEFAULT_CHANNEL = "ctrl.rover_1.dispatch"
CHANNEL_KEY = "bus.channel"
MARGIN = 16
MAX_ROWS = 6
FIRST_ROW_Y = 96
ROW_HEIGHT = 18


def draw_pending(comms, channel):
    messages = comms.pending(channel)
    panel.draw_text(MARGIN, 80, str(len(messages)) + " pending", 12, "text-secondary")
    for index, message in enumerate(messages[:MAX_ROWS]):
        line = format_message(message.id, message.sender, message.tick, message.value)
        panel.draw_text(MARGIN, FIRST_ROW_Y + index * ROW_HEIGHT, line, 12, "text-bright")


def draw_latest(comms, channel):
    info = comms.latest_info(channel)
    if info is None:
        text = "no broadcast on this channel"
    else:
        text = "broadcast: " + short_text(info.value, 70)
    panel.draw_text(MARGIN + 400, 80, text, 12, "text-value")


while True:
    panel.clear()
    width = panel.width()
    height = panel.height()
    panel.card(4, 4, width - 8, height - 8, "SIGNAL BUS")
    channel = panel.text_field(
        CHANNEL_KEY, MARGIN, 36, 360, DEFAULT_CHANNEL, "channel name", "Channel"
    )
    if not valid_channel(channel):
        hint = "Use letters, digits, _ . : - (1-64 characters)"
        panel.draw_text(MARGIN + 380, 56, hint, 11, "error")
    else:
        comms = get_component("comms")
        if comms is None:
            panel.draw_text(MARGIN, 80, "Signal Bus not researched yet", 13, "text-muted")
        else:
            draw_pending(comms, channel)
            draw_latest(comms, channel)
