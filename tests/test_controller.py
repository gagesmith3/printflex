from types import SimpleNamespace

import pytest

from printflex.controller import DONE, IDLE, LOADED, PRINTING, ControllerError, PrinterController
from printflex.settings import Settings

JOB = {"id": "job-1", "card": {"first": "ADA", "last": "LOVELACE"}}
JOB2 = {"id": "job-2", "card": {"first": "GRACE", "last": "HOPPER"}}


class RecordingEvents:
    def __init__(self):
        self.published = []

    def publish(self, event, data):
        self.published.append((event, data))


class RecordingHardware:
    def __init__(self):
        self.phases = []

    def on_phase(self, phase, job):
        self.phases.append(phase)


@pytest.fixture
def rig(tmp_path, scheduler):
    settings = Settings(tmp_path / "settings.json")
    settings.update({"phases": {"receive": 1, "compose": 2, "print": 3}, "hold_seconds": 5})
    events = RecordingEvents()
    hardware = RecordingHardware()
    controller = PrinterController(settings, events, hardware, scheduler=scheduler, clock=scheduler.clock)
    return SimpleNamespace(controller=controller, events=events, hardware=hardware, scheduler=scheduler, settings=settings)


def test_auto_mode_runs_full_cycle(rig):
    snapshot = rig.controller.submit(JOB)
    assert snapshot["state"] == PRINTING
    assert [p["duration"] for p in snapshot["phases"]] == [1, 2, 3]

    rig.scheduler.advance(5)
    assert rig.controller.state == PRINTING
    rig.scheduler.advance(1)
    assert rig.controller.state == DONE
    rig.scheduler.advance(5)
    assert rig.controller.state == IDLE
    assert rig.hardware.phases == ["receive", "compose", "print", "done", "idle"]


def test_snapshot_reports_elapsed_time(rig):
    rig.controller.submit(JOB)
    rig.scheduler.advance(2.5)
    assert rig.controller.snapshot()["elapsed"] == 2.5


def test_cue_mode_waits_for_start(rig):
    rig.settings.update({"mode": "cue"})
    assert rig.controller.submit(JOB)["state"] == LOADED
    rig.scheduler.advance(100)
    assert rig.controller.state == LOADED
    assert rig.controller.start()["state"] == PRINTING


def test_submit_while_loaded_replaces_job(rig):
    rig.settings.update({"mode": "cue"})
    rig.controller.submit(JOB)
    assert rig.controller.submit(JOB2)["job"]["id"] == "job-2"


def test_submit_is_busy_while_printing_and_done(rig):
    rig.controller.submit(JOB)
    with pytest.raises(ControllerError) as exc:
        rig.controller.submit(JOB2)
    assert exc.value.code == "busy"

    rig.scheduler.advance(6)
    assert rig.controller.state == DONE
    with pytest.raises(ControllerError):
        rig.controller.submit(JOB2)


def test_start_requires_loaded_job(rig):
    with pytest.raises(ControllerError) as exc:
        rig.controller.start()
    assert exc.value.code == "not_loaded"


def test_reset_mid_print_cancels_timers(rig):
    rig.controller.submit(JOB)
    rig.scheduler.advance(2)
    assert rig.controller.reset()["state"] == IDLE
    rig.scheduler.advance(100)
    assert rig.controller.state == IDLE
    assert rig.hardware.phases == ["receive", "compose", "idle"]


def test_replay_restarts_last_job(rig):
    with pytest.raises(ControllerError) as exc:
        rig.controller.replay()
    assert exc.value.code == "no_job"

    rig.controller.submit(JOB)
    rig.scheduler.advance(6)
    snapshot = rig.controller.replay()
    assert snapshot["state"] == PRINTING
    assert snapshot["job"]["id"] == "job-1"
    assert snapshot["elapsed"] == 0

    rig.scheduler.advance(2)
    rig.controller.replay()  # restart mid-print
    rig.scheduler.advance(5)
    assert rig.controller.state == PRINTING
    rig.scheduler.advance(1)
    assert rig.controller.state == DONE


def test_replay_in_cue_mode_loads(rig):
    rig.controller.submit(JOB)
    rig.scheduler.advance(6)
    rig.settings.update({"mode": "cue"})
    assert rig.controller.replay()["state"] == LOADED


def test_hold_zero_keeps_card_until_reset(rig):
    rig.settings.update({"hold_seconds": 0})
    rig.controller.submit(JOB)
    rig.scheduler.advance(1000)
    assert rig.controller.state == DONE
    assert rig.controller.reset()["state"] == IDLE


def test_speed_scales_phase_durations(rig):
    rig.settings.update({"speed": 2})
    assert [p["duration"] for p in rig.controller.submit(JOB)["phases"]] == [0.5, 1, 1.5]


def test_transitions_are_published_in_order(rig):
    rig.controller.submit(JOB)
    rig.scheduler.advance(11)
    published = [data for event, data in rig.events.published if event == "state"]
    assert [data["state"] for data in published] == [PRINTING, DONE, IDLE]
    assert [data["seq"] for data in published] == [1, 2, 3]


def test_protected_ids_include_last_job(rig):
    rig.controller.submit(JOB)
    rig.controller.reset()
    assert rig.controller.protected_job_ids() == {"job-1"}


def test_hardware_failure_does_not_stop_printing(rig):
    def explode(phase, job):
        raise RuntimeError("motor jammed")

    rig.hardware.on_phase = explode
    rig.controller.submit(JOB)
    rig.scheduler.advance(6)
    assert rig.controller.state == DONE
