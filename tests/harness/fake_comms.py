"""Fake Signal Bus (`comms`) for tests: the parts of the in-game API our scripts use.

Behaviour follows docs/game/signal-bus.md (VERIFIED docs, build fe9a45c): a queue message is
taken by exactly one receiver, `receive` consumes, `pending` and `latest` do not, and a broadcast
replaces the channel's value. Only names we call are implemented; anything else raises
AttributeError, the same way the test component fake does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from tests.harness.fake_game import FakeComponent

CHANNEL_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


@dataclass
class FakeSignalBus:
    queues: dict[str, list[SimpleNamespace]] = field(default_factory=dict)
    broadcasts: dict[str, SimpleNamespace] = field(default_factory=dict)
    next_id: int = 1
    sender: str = "test"

    def _check_channel(self, channel: str) -> bool:
        return isinstance(channel, str) and CHANNEL_PATTERN.match(channel) is not None

    def send(self, channel: str, value: Any) -> SimpleNamespace:
        if not self._check_channel(channel):
            return SimpleNamespace(status="invalid_channel", message="bad channel", message_id=None)
        message = SimpleNamespace(id=self.next_id, sender=self.sender, tick=0, value=value)
        self.next_id += 1
        self.queues.setdefault(channel, []).append(message)
        return SimpleNamespace(status="ok", message="", message_id=message.id)

    def pending(self, channel: str) -> list[SimpleNamespace]:
        if not self._check_channel(channel):
            raise ValueError(f"malformed channel: {channel!r}")
        return [SimpleNamespace(**vars(m)) for m in self.queues.get(channel, [])]

    def receive(self, channel: str, message_id: int | None = None) -> SimpleNamespace:
        if not self._check_channel(channel):
            return SimpleNamespace(status="invalid_channel", message="bad channel", packet=None)
        queue = self.queues.get(channel, [])
        # Without an id, an empty queue is "empty"; with an id, a missing message is "not_found"
        # even when the queue is empty (manual: an id already received gives not_found).
        if message_id is None:
            if not queue:
                return SimpleNamespace(status="empty", message="no message", packet=None)
            return SimpleNamespace(status="ok", message="", packet=queue.pop(0))
        index = _index_of(queue, message_id)
        if index is None:
            return SimpleNamespace(status="not_found", message="no such message", packet=None)
        return SimpleNamespace(status="ok", message="", packet=queue.pop(index))

    def cancel(self, channel: str, message_id: int) -> SimpleNamespace:
        queue = self.queues.get(channel, [])
        index = _index_of(queue, message_id)
        if index is None:
            return SimpleNamespace(status="not_found", message="no such message")
        queue.pop(index)
        return SimpleNamespace(status="ok", message="")

    def broadcast(self, channel: str, value: Any) -> SimpleNamespace:
        if not self._check_channel(channel):
            return SimpleNamespace(status="invalid_channel", message="bad channel")
        self.broadcasts[channel] = SimpleNamespace(value=value, sender=self.sender, age_seconds=0.0)
        return SimpleNamespace(status="ok", message="")

    def latest(self, channel: str) -> Any:
        if not self._check_channel(channel):
            raise ValueError(f"malformed channel: {channel!r}")
        current = self.broadcasts.get(channel)
        return None if current is None else current.value

    def latest_info(self, channel: str) -> SimpleNamespace | None:
        return self.broadcasts.get(channel)

    def as_component(self) -> FakeComponent:
        """The bus as `get_component("comms")` returns it."""
        methods = {
            name: getattr(self, name)
            for name in ("send", "pending", "receive", "cancel", "broadcast", "latest")
        }
        methods["latest_info"] = self.latest_info
        return FakeComponent(id="comms", type_id="comms", methods=methods)


def _index_of(queue: list[SimpleNamespace], message_id: int) -> int | None:
    for index, message in enumerate(queue):
        if message.id == message_id:
            return index
    return None
