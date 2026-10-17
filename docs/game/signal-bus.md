# Signal Bus

Source: in-game DOCS manual, build `fe9a45c`. Sections: "Signal Bus" (manual `55-signal-bus.md` and `193-signal-bus.md`), "Data Archive" (for the contrast). Tag: **VERIFIED (docs)**. Short notes, own words.

## Access and unlock

- `get_component("comms")` returns the bus after **Signal Bus** research. Before that it returns `None`.
- Libraries and built-ins do not need this research. The bus is separate from the Data Archive (`notebook`).

## Two kinds of traffic

- **Queue** (`send`, `receive`, `pending`, `cancel`, `update`): each message is taken by one receiver. Use it for jobs.
- **Broadcast** (`broadcast`, `latest`, `latest_info`): one current value per channel. Every reader sees it until it is replaced or cleared. Use it for status and "what is true now".
- `receive()` consumes. `latest()` does not.

## Methods we use (`comms`)

| Method | Returns | Notes |
|--------|---------|-------|
| `send(channel, value)` | SendResult (`.status`, `.message`, `.message_id`) | `.message_id` is set only when `status == "ok"`. Keep it to cancel or update later. |
| `pending(channel)` | list of CommsMessage (`.id`, `.sender`, `.tick`, `.value`) | Read-only copy, oldest first. Takes nothing. A malformed channel raises `ValueError`. |
| `receive(channel, message_id=None)` | ReceiveResult (`.status`, `.message`, `.packet`) | Omit the id to take the oldest. With an id, takes only that message. `.packet` is set only on `"ok"`. Statuses include `"empty"` and `"not_found"`. |
| `cancel(channel, message_id)` | ActionResult | Removes one waiting message. `"not_found"` if already taken. |
| `update(channel, message_id, value)` | ActionResult | Replaces the whole value of a waiting message. Keeps its id and place. |
| `broadcast(channel, value)` | ActionResult | Replaces the channel's current value. Publishing the same value again counts. |
| `latest(channel)` | the value, or `None` | Read-only. A missing channel gives `None`. Malformed channel raises `ValueError`. |
| `latest_info(channel)` | BroadcastInfo (`.value`, `.sender`, `.age_seconds`) or `None` | Age is in simulation seconds and freezes while paused. |

Choosing one job by id (manual pattern): read `pending()`, pick the id you want, then `receive(channel, id)`. The take is one operation: if another worker got it first, the result is `"not_found"` and you take nothing else.

## Limits (manual, Signal Bus)

- Channel id: 1 to 64 characters from letters, digits, `_`, `.`, `:`, `-`.
- Value: JSON-safe. Up to 8 nested levels, 1,024 values in total, 4,096 characters per string or key. Functions, components, sets and class instances give `"invalid_value"`.
- A queue holds up to 64 messages. A save holds up to 512 channels.
- Always branch on `.status`. `.message` gives the reason text.

## Behaviour to design for

- A worker that has received a job owns finishing it. Cancelling after receipt does not stop the work.
- Stopping or restarting a script drops its waits. Queued messages stay queued.
- Save and load keep queued messages and the latest broadcast, not a script's local variables.
- A running script restarts from line one after a game load (see `language.md`). Keep any state that must survive in the Data Archive or on the bus.

## Not used yet

- `wait`, `wait_any`, `wait_broadcast` block the calling script with no timeout. We poll `pending()` in the pass loop instead, so a machine keeps scanning or moving.
- `clear`, `channels`, `queue_size`: available, not used.
