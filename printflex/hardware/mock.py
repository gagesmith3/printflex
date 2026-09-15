import logging

from .base import Hardware

log = logging.getLogger(__name__)


class MockHardware(Hardware):
    """Stands in for real props: logs what the hardware would be told to do."""

    def on_phase(self, phase: str, job: dict | None) -> None:
        log.info("hardware: %s%s", phase, f" job={job['id']}" if job else "")
