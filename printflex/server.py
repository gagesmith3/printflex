"""Server side: the display screen, the crew panel, and the APIs they share."""

import re

from flask import Blueprint, Response, abort, jsonify, render_template, request, send_from_directory

from .controller import ControllerError
from .extensions import services

bp = Blueprint("server", __name__, url_prefix="/server")

_JOB_ID = re.compile(r"^[0-9a-f-]+$")


@bp.get("/display")
def display():
    return render_template("display.html", base_url=services().base_url)


@bp.get("/operator")
def operator():
    return render_template("operator.html", base_url=services().base_url)


@bp.get("/api/state")
def state():
    svc = services()
    return jsonify(state=svc.controller.snapshot(), settings=svc.settings.snapshot())


@bp.get("/api/events")
def events():
    svc = services()

    def initial():
        return [("settings", svc.settings.snapshot()), ("state", svc.controller.snapshot())]

    return Response(
        svc.events.stream(initial),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.post("/api/control/<action>")
def control(action: str):
    controller = services().controller
    handlers = {"start": controller.start, "replay": controller.replay, "reset": controller.reset}
    if action not in handlers:
        abort(404)
    try:
        return jsonify(ok=True, state=handlers[action]())
    except ControllerError as exc:
        return jsonify(error=exc.code, message=exc.message), 409


@bp.get("/api/settings")
def get_settings():
    return jsonify(services().settings.snapshot())


@bp.post("/api/settings")
def update_settings():
    svc = services()
    try:
        values = svc.settings.update(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify(error="invalid", message=str(exc)), 400
    svc.events.publish("settings", values)
    return jsonify(values)


@bp.get("/photos/<job_id>.jpg")
def photo(job_id: str):
    if not _JOB_ID.match(job_id):
        abort(404)
    return send_from_directory(services().upload_dir, f"{job_id}.jpg", max_age=0)
