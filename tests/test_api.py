import io
from pathlib import Path

import pytest


def submit(client, photo: bytes | None = None, **form):
    data = {"first": "Ada", "last": "Lovelace", **form}
    if photo is not None:
        data["photo"] = (io.BytesIO(photo), "photo.jpg")
    return client.post("/user/api/submit", data=data, content_type="multipart/form-data")


@pytest.mark.parametrize("path", ["/user/", "/server/display", "/server/operator"])
def test_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b"printflex" in response.data.lower()


def test_root_redirects_to_phone_page(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user/")


def test_submit_prints_in_auto_mode(client, jpeg):
    response = submit(client, jpeg())
    assert response.status_code == 200
    state = response.get_json()["state"]
    assert state["state"] == "printing"
    assert (state["job"]["card"]["first"], state["job"]["card"]["last"]) == ("ADA", "LOVELACE")

    photo = client.get(state["job"]["photo_url"])
    assert photo.status_code == 200
    assert photo.mimetype == "image/jpeg"
    photo.close()


@pytest.mark.parametrize(
    "form,with_photo,message",
    [
        ({"first": ""}, True, "ENTER FIRST NAME"),
        ({}, False, "TAKE A PHOTO FIRST"),
        ({"dob": "nope"}, True, "DOB MUST BE A DATE"),
    ],
)
def test_submit_validation(client, jpeg, form, with_photo, message):
    response = submit(client, jpeg() if with_photo else None, **form)
    assert response.status_code == 400
    assert response.get_json()["message"] == message


def test_submit_rejects_non_image(client):
    response = submit(client, b"definitely not a jpeg")
    assert response.status_code == 400
    assert response.get_json()["message"] == "COULD NOT READ PHOTO"


def test_submit_rejects_oversized_upload(app, client, jpeg):
    app.config["MAX_CONTENT_LENGTH"] = 1000
    response = submit(client, jpeg())
    assert response.status_code == 413
    assert response.get_json()["error"] == "too_large"


def test_submit_while_printing_is_busy(client, jpeg):
    assert submit(client, jpeg()).status_code == 200
    response = submit(client, jpeg())
    assert response.status_code == 409
    assert response.get_json()["error"] == "busy"


def test_cue_mode_start_reset_replay(client, jpeg):
    client.post("/server/api/settings", json={"mode": "cue"})
    assert submit(client, jpeg()).get_json()["state"]["state"] == "loaded"
    assert client.post("/server/api/control/start").get_json()["state"]["state"] == "printing"
    assert client.post("/server/api/control/reset").get_json()["state"]["state"] == "idle"
    assert client.post("/server/api/control/replay").get_json()["state"]["state"] == "loaded"
    assert client.post("/server/api/control/panic").get_json()["state"]["panic"] is True


def test_control_errors(client):
    response = client.post("/server/api/control/start")
    assert response.status_code == 409
    assert response.get_json()["error"] == "not_loaded"
    assert client.post("/server/api/control/explode").status_code == 404


def test_settings_update_validate_and_persist(app, client):
    response = client.post("/server/api/settings", json={"speed": 2, "phases": {"print": 10}})
    assert response.status_code == 200
    assert response.get_json()["phases"]["print"] == 10.0

    assert client.post("/server/api/settings", json={"speed": 99}).status_code == 400
    assert client.post("/server/api/settings", data="nope").status_code == 400
    assert client.get("/server/api/settings").get_json()["speed"] == 2.0
    assert (Path(app.config["DATA_DIR"]) / "settings.json").exists()


def test_photo_route_rejects_bad_ids(client):
    assert client.get("/server/photos/nope.jpg").status_code == 404
    assert client.get("/server/photos/..%2Fsettings.jpg").status_code == 404


def test_event_stream_sends_snapshot_then_updates(app):
    svc = app.extensions["printflex"]
    stream = svc.events.stream(lambda: [("state", svc.controller.snapshot())])
    assert next(stream).startswith("retry:")
    assert next(stream).startswith("event: state\n")
    svc.events.publish("settings", {"x": 1})
    assert next(stream) == 'event: settings\ndata: {"x":1}\n\n'
    stream.close()
    assert svc.events.client_count == 0


def test_event_endpoint_is_an_event_stream(client):
    response = client.get("/server/api/events", buffered=False)
    assert response.mimetype == "text/event-stream"
    response.close()
