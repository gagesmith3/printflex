from flask import current_app


def services():
    """Shared objects built in create_app(): settings, events, hardware, controller, upload_dir, base_url, world_date."""
    return current_app.extensions["printflex"]
