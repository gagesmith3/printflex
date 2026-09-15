"""Server-Sent Events broadcaster shared by the display, phone, and crew pages."""

import json
import queue
import threading
from collections.abc import Callable, Iterable, Iterator

HEARTBEAT_SECONDS = 15.0


def format_event(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


class EventBroker:
    def __init__(self, heartbeat: float = HEARTBEAT_SECONDS):
        self._heartbeat = heartbeat
        self._clients: set[queue.Queue] = set()
        self._lock = threading.Lock()

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def publish(self, event: str, data) -> None:
        message = format_event(event, data)
        with self._lock:
            clients = list(self._clients)
        for client in clients:
            try:
                client.put_nowait(message)
            except queue.Full:
                pass  # client stopped reading; the heartbeat write will drop it

    def stream(self, initial: Callable[[], Iterable[tuple[str, object]]]) -> Iterator[str]:
        """Yield SSE messages for one client until it disconnects.

        Subscribes before building the initial snapshot so nothing published in between is lost.
        """
        client: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._clients.add(client)
        try:
            yield "retry: 2000\n\n"
            for event, data in initial():
                yield format_event(event, data)
            while True:
                try:
                    yield client.get(timeout=self._heartbeat)
                except queue.Empty:
                    yield ": ping\n\n"
        finally:
            with self._lock:
                self._clients.discard(client)
