"""PrintFlex: Flask server for a movie prop that "prints" driver's licenses on screen."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, jsonify, redirect, url_for

from .config import Config
from .controller import PrinterController
from .events import EventBroker
from .hardware import get_hardware
from .netinfo import base_url
from .settings import Settings


def create_app(overrides: dict | None = None, scheduler=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(overrides or {})

    data_dir = Path(app.config["DATA_DIR"])
    upload_dir = data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    world_date = app.config["WORLD_DATE"]

    settings = Settings(data_dir / "settings.json")
    events = EventBroker()
    hardware = get_hardware(app.config)
    controller = PrinterController(settings, events, hardware, scheduler=scheduler)
    hardware.bind(controller)

    app.extensions["printflex"] = SimpleNamespace(
        settings=settings,
        events=events,
        hardware=hardware,
        controller=controller,
        upload_dir=upload_dir,
        base_url=base_url(app.config["PUBLIC_HOST"], app.config["PORT"]),
        world_date=date.fromisoformat(world_date) if world_date else None,
    )

    from . import server, user

    app.register_blueprint(user.bp)
    app.register_blueprint(server.bp)

    @app.get("/")
    def home():
        return redirect(url_for("user.index"))

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="too_large", message="PHOTO TOO LARGE"), 413

    @app.context_processor
    def branding():
        return {
            "software_name": app.config["SOFTWARE_NAME"],
            "state_name": app.config["STATE_NAME"],
            "state_abbr": app.config["STATE_ABBR"],
        }

    return app
