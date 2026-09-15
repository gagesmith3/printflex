"""Phone side: take a photo, enter a name, send it to the printer."""

import secrets
from datetime import date, datetime

from flask import Blueprint, current_app, jsonify, render_template, request, url_for

from .controller import ControllerError
from .extensions import services
from .idgen import ALLOWED_SEXES, EYES, HAIR, OVERRIDE_FIELDS, clean_name, generate_card
from .images import InvalidImage, process_photo, prune_photos

bp = Blueprint("user", __name__, url_prefix="/user")


def _error(code: str, message: str, status: int):
    return jsonify(error=code, message=message), status


def _new_job_id() -> str:
    return f"{datetime.now():%Y%m%d-%H%M%S-%f}-{secrets.token_hex(2)}"


@bp.get("/")
def index():
    return render_template("user.html", sexes=ALLOWED_SEXES, eyes=EYES, hair=HAIR)


@bp.post("/api/submit")
def submit():
    svc = services()
    if svc.controller.is_busy():
        return _error("busy", "PRINTER BUSY", 409)

    try:
        first = clean_name(request.form.get("first"), "FIRST")
        last = clean_name(request.form.get("last"), "LAST")
        card = generate_card(
            first,
            last,
            current_app.config["STATE_NAME"],
            current_app.config["STATE_ABBR"],
            overrides={field: request.form.get(field, "") for field in OVERRIDE_FIELDS},
            today=svc.world_date or date.today(),
        )
    except ValueError as exc:
        return _error("invalid", str(exc), 400)

    photo = request.files.get("photo")
    if photo is None:
        return _error("invalid", "TAKE A PHOTO FIRST", 400)

    job_id = _new_job_id()
    photo_path = svc.upload_dir / f"{job_id}.jpg"
    try:
        process_photo(photo.stream, photo_path)
    except InvalidImage:
        return _error("invalid", "COULD NOT READ PHOTO", 400)

    job = {"id": job_id, "photo_url": url_for("server.photo", job_id=job_id), "card": card}
    try:
        snapshot = svc.controller.submit(job)
    except ControllerError as exc:
        photo_path.unlink(missing_ok=True)
        return _error(exc.code, exc.message, 409)

    prune_photos(svc.upload_dir, current_app.config["MAX_PHOTOS"], protect=svc.controller.protected_job_ids())
    return jsonify(ok=True, state=snapshot)
