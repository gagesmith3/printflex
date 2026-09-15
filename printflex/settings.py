"""Crew-adjustable settings, persisted to data/settings.json."""

import copy
import json
import os
import threading
from pathlib import Path

PHASES = ("receive", "compose", "print")

DEFAULTS = {
    "mode": "auto",  # "auto" prints on arrival, "cue" waits for START
    "speed": 1.0,  # 2.0 = twice as fast
    "phases": {"receive": 2.0, "compose": 4.0, "print": 5.0},  # seconds at speed 1.0
    "hold_seconds": 8.0,  # 0 = hold the finished card until RESET
    "scanlines": 0.35,
    "show_connection_info": False,
}


def _number(lo: float, hi: float):
    def check(raw, _current):
        if isinstance(raw, bool):
            raise ValueError("expected a number")
        value = float(raw)
        if not lo <= value <= hi:
            raise ValueError(f"must be between {lo} and {hi}")
        return value

    return check


def _mode(raw, _current):
    if raw not in ("auto", "cue"):
        raise ValueError("must be 'auto' or 'cue'")
    return raw


def _bool(raw, _current):
    if not isinstance(raw, bool):
        raise ValueError("expected true or false")
    return raw


def _phases(raw, current):
    if not isinstance(raw, dict):
        raise ValueError("expected an object of phase durations")
    merged = dict(current)
    for name, seconds in raw.items():
        if name not in PHASES:
            raise ValueError(f"unknown phase {name!r}")
        merged[name] = _number(0, 120)(seconds, None)
    return merged


VALIDATORS = {
    "mode": _mode,
    "speed": _number(0.25, 4),
    "phases": _phases,
    "hold_seconds": _number(0, 3600),
    "scanlines": _number(0, 1),
    "show_connection_info": _bool,
}


def _apply(values: dict, changes, strict: bool = True) -> dict:
    if not isinstance(changes, dict):
        raise ValueError("settings must be a JSON object")
    result = copy.deepcopy(values)
    for key, raw in changes.items():
        if key not in VALIDATORS:
            continue
        try:
            result[key] = VALIDATORS[key](raw, result[key])
        except (TypeError, ValueError) as exc:
            if strict:
                raise ValueError(f"{key}: {exc}") from None
    return result


class Settings:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        self._values = copy.deepcopy(DEFAULTS)
        stored = self._read()
        if isinstance(stored, dict):
            # Skip bad values rather than refusing to start over a hand-edited file.
            self._values = _apply(self._values, stored, strict=False)

    def snapshot(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._values)

    def get(self, key: str):
        with self._lock:
            return copy.deepcopy(self._values[key])

    def update(self, changes) -> dict:
        with self._lock:
            self._values = _apply(self._values, changes)
            self._write()
            return copy.deepcopy(self._values)

    def phase_plan(self) -> list[dict]:
        """Phase durations for the next print, with the speed multiplier applied."""
        with self._lock:
            speed = self._values["speed"]
            return [
                {"name": name, "duration": round(self._values["phases"][name] / speed, 3)}
                for name in PHASES
            ]

    def _read(self):
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _write(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._values, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)
