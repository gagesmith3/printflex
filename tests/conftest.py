import io

import pytest
from PIL import Image

from printflex import create_app


class FakeTimer:
    def __init__(self, due: float, callback):
        self.due = due
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class FakeScheduler:
    """Runs scheduled callbacks only when a test calls advance(), in due-time order."""

    def __init__(self):
        self.now = 0.0
        self._timers: list[FakeTimer] = []

    def clock(self) -> float:
        return self.now

    def call_later(self, delay: float, callback) -> FakeTimer:
        timer = FakeTimer(self.now + max(delay, 0.0), callback)
        self._timers.append(timer)
        return timer

    def advance(self, seconds: float) -> None:
        target = self.now + seconds
        while True:
            due = [t for t in self._timers if not t.cancelled and t.due <= target]
            if not due:
                break
            timer = min(due, key=lambda t: t.due)
            self._timers.remove(timer)
            self.now = timer.due
            timer.callback()
        self.now = target


def make_jpeg(size=(800, 1000), color="red", orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    options = {}
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        options["exif"] = exif
    image.save(buffer, "JPEG", **options)
    return buffer.getvalue()


@pytest.fixture
def scheduler():
    return FakeScheduler()


@pytest.fixture
def jpeg():
    return make_jpeg


@pytest.fixture
def app(tmp_path, scheduler):
    return create_app(
        {"TESTING": True, "DATA_DIR": tmp_path, "PUBLIC_HOST": "test.local", "WORLD_DATE": ""},
        scheduler=scheduler,
    )


@pytest.fixture
def client(app):
    return app.test_client()
