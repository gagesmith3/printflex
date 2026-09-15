"""Printer state machine: the single source of truth that every page and prop reacts to."""

import logging
import threading
import time
import uuid
from collections.abc import Callable

log = logging.getLogger(__name__)

IDLE = "idle"
LOADED = "loaded"
PRINTING = "printing"
DONE = "done"


class ControllerError(Exception):
    """An action that isn't allowed right now. `code` goes to the client, `message` is shown."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ThreadingScheduler:
    def call_later(self, delay: float, callback: Callable[[], None]):
        timer = threading.Timer(max(delay, 0.0), callback)
        timer.daemon = True
        timer.start()
        return timer


def _job_summary(job: dict | None) -> dict | None:
    if job is None:
        return None
    card = job.get("card", {})
    return {"id": job["id"], "name": f"{card.get('last', '')}, {card.get('first', '')}".strip(", ")}


class PrinterController:
    """IDLE -> (LOADED) -> PRINTING -> DONE -> IDLE.

    The server owns the timeline. Each change bumps `seq` and is published to SSE
    clients. `run` (the generation) changes only on state transitions, and every
    scheduled callback carries the generation it was created in, so callbacks left
    over from before a RESET or REPLAY do nothing. The panic screen is independent
    of the state: printing carries on underneath it.
    """

    def __init__(self, settings, events, hardware, scheduler=None, clock=time.monotonic):
        self._settings = settings
        self._events = events
        self._hardware = hardware
        self._scheduler = scheduler or ThreadingScheduler()
        self._clock = clock
        self._lock = threading.RLock()
        self._boot_id = uuid.uuid4().hex[:8]
        self._seq = 0
        self._generation = 0
        self._timers = []
        self._state = IDLE
        self._job = None
        self._last_job = None
        self._phases = []
        self._started_at = None
        self._panic = False

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def is_busy(self) -> bool:
        with self._lock:
            return self._state in (PRINTING, DONE)

    def protected_job_ids(self) -> set[str]:
        """Jobs whose photos must survive pruning."""
        with self._lock:
            return {job["id"] for job in (self._job, self._last_job) if job}

    def snapshot(self) -> dict:
        with self._lock:
            elapsed = None
            if self._started_at is not None:
                elapsed = round(self._clock() - self._started_at, 3)
            return {
                "boot_id": self._boot_id,
                "seq": self._seq,
                "run": self._generation,
                "panic": self._panic,
                "state": self._state,
                "job": self._job,
                "phases": self._phases,
                "elapsed": elapsed,
                "last_job": _job_summary(self._last_job),
            }

    # Actions -----------------------------------------------------------------

    def submit(self, job: dict) -> dict:
        with self._lock:
            if self._state in (PRINTING, DONE):
                raise ControllerError("busy", "PRINTER BUSY")
            self._last_job = job
            self._begin(job)
            return self.snapshot()

    def start(self) -> dict:
        with self._lock:
            if self._state != LOADED:
                raise ControllerError("not_loaded", "NOTHING LOADED TO PRINT")
            self._enter_printing(self._job)
            return self.snapshot()

    def replay(self) -> dict:
        with self._lock:
            if self._last_job is None:
                raise ControllerError("no_job", "NOTHING TO REPLAY YET")
            self._begin(self._last_job)
            return self.snapshot()

    def reset(self) -> dict:
        with self._lock:
            self._enter_idle()
            return self.snapshot()

    def toggle_panic(self) -> dict:
        """Cover the display with the decoy screen, or uncover it."""
        with self._lock:
            self._panic = not self._panic
            self._publish()
            return self.snapshot()

    # Transitions -------------------------------------------------------------

    def _begin(self, job: dict) -> None:
        if self._settings.get("mode") == "cue":
            self._enter_loaded(job)
        else:
            self._enter_printing(job)

    def _enter_loaded(self, job: dict) -> None:
        self._cancel_timers()
        self._set(LOADED, job)
        self._notify_hardware("loaded", job)
        self._publish()

    def _enter_printing(self, job: dict) -> None:
        self._cancel_timers()
        phases = self._settings.phase_plan()
        self._set(PRINTING, job, phases, started_at=self._clock())
        offset = 0.0
        for phase in phases:
            self._schedule(offset, self._notify_hardware, phase["name"], job)
            offset += phase["duration"]
        self._schedule(offset, self._enter_done)
        self._publish()

    def _enter_done(self) -> None:
        self._cancel_timers()
        job = self._job
        self._set(DONE, job, self._phases)
        self._notify_hardware("done", job)
        hold = self._settings.get("hold_seconds")
        if hold > 0:
            self._schedule(hold, self._enter_idle)
        self._publish()

    def _enter_idle(self) -> None:
        self._cancel_timers()
        self._set(IDLE, None)
        self._notify_hardware("idle", None)
        self._publish()

    # Helpers -----------------------------------------------------------------

    def _set(self, state: str, job, phases=None, started_at=None) -> None:
        self._state = state
        self._job = job
        self._phases = phases or []
        self._started_at = started_at

    def _schedule(self, delay: float, callback: Callable, *args) -> None:
        generation = self._generation

        def fire():
            with self._lock:
                if generation == self._generation:
                    callback(*args)

        self._timers.append(self._scheduler.call_later(delay, fire))

    def _cancel_timers(self) -> None:
        self._generation += 1
        for timer in self._timers:
            timer.cancel()
        self._timers.clear()

    def _notify_hardware(self, phase: str, job) -> None:
        try:
            self._hardware.on_phase(phase, job)
        except Exception:
            log.exception("hardware hook failed during %s", phase)

    def _publish(self) -> None:
        self._seq += 1
        self._events.publish("state", self.snapshot())
