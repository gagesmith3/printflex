"""Interface between the printer controller and physical props (motors, lights, buttons)."""


class Hardware:
    """Base class; every hook is a no-op.

    A future UNO Q implementation will call functions the Arduino sketch exposes with
    Bridge.provide() through arduino-router, and route physical button presses to
    controller.start() / replay() / reset() / toggle_panic(). Hooks run while the controller holds its
    lock, so they must return quickly and hand slow work to a thread.
    """

    controller = None

    def bind(self, controller) -> None:
        self.controller = controller

    def on_phase(self, phase: str, job: dict | None) -> None:
        """Called at each step: loaded, receive, compose, print, done, idle."""

    def close(self) -> None:
        """Release devices on shutdown."""
