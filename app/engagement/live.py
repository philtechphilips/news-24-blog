"""Pushes activity on a post (comments, likes, shares) to everyone reading it.

Each open GET /posts/{id}/live stream subscribes here; routes publish an event
after they change something, and every subscriber of that post receives it.

Subscribers live in this server process's memory. That's right for one
process (`fastapi dev` / `fastapi run`); with several workers or servers,
replace publish/subscribe with a shared broker such as Redis pub/sub.
"""

import asyncio
import threading
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

Event = tuple[str, Any]

# Events waiting for one slow reader before it's told to reload instead.
QUEUE_SIZE = 100

# Tells a reader to load the post's comments and counts again.
READY: Event = ("ready", {})

Subscriber = tuple[asyncio.AbstractEventLoop, asyncio.Queue[Event]]


class LiveHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[UUID, set[Subscriber]] = defaultdict(set)

    @asynccontextmanager
    async def subscribe(self, post_id: UUID) -> AsyncIterator[asyncio.Queue[Event]]:
        """Receive this post's events until the `async with` block exits."""
        subscriber: Subscriber = (asyncio.get_running_loop(), asyncio.Queue(QUEUE_SIZE))
        with self._lock:
            self._subscribers[post_id].add(subscriber)
        try:
            yield subscriber[1]
        finally:
            with self._lock:
                subscribers = self._subscribers[post_id]
                subscribers.discard(subscriber)
                if not subscribers:
                    del self._subscribers[post_id]

    def subscriber_count(self, post_id: UUID) -> int:
        with self._lock:
            return len(self._subscribers.get(post_id, ()))

    def publish(self, post_id: UUID, event: str, data: Any) -> None:
        """Send an event to everyone reading the post. `data` must be
        JSON-serialisable. Safe to call from sync routes, which FastAPI runs
        in worker threads."""
        with self._lock:
            subscribers = list(self._subscribers.get(post_id, ()))
        for loop, queue in subscribers:
            try:
                loop.call_soon_threadsafe(_offer, queue, (event, data))
            except RuntimeError:
                pass  # That reader's event loop has shut down.


def _offer(queue: asyncio.Queue[Event], event: Event) -> None:
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        # The reader has fallen far behind. Drop its backlog and have it
        # reload everything, which is cheaper than replaying each event.
        while not queue.empty():
            queue.get_nowait()
        queue.put_nowait(READY)


hub = LiveHub()
