// Phone page: take a photo, enter a name, send it to the display.
(function () {
  "use strict";

  const { connectEvents, latestState, post } = window.PrintFlex;
  const MAX_EDGE = 1600;
  const LABELS = { idle: "ready", loaded: "loaded", printing: "busy", done: "busy", offline: "no link" };

  const $ = (id) => document.getElementById(id);
  const form = $("capture-form");
  const preview = $("preview");
  const sendButton = $("send");
  const message = $("message");

  let photoBlob = null;
  let printerState = "offline";
  let sending = false;

  function say(text, isError) {
    message.textContent = text ? "> " + text : "";
    message.className = "out" + (isError ? " out--error" : "");
  }

  function updateSendButton() {
    const busy = printerState === "printing" || printerState === "done";
    sendButton.disabled = sending || busy;
    sendButton.textContent = sending ? "sending" : busy ? "busy" : "send";
  }

  function setStatus(state) {
    printerState = state;
    $("status").dataset.state = state;
    $("status").textContent = LABELS[state];
    updateSendButton();
  }

  // Re-encode to a JPEG no larger than MAX_EDGE. The browser applies EXIF rotation and
  // decodes formats like HEIC, so the upload is small and predictable.
  function downscale(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        URL.revokeObjectURL(url);
        const scale = Math.min(1, MAX_EDGE / Math.max(img.naturalWidth, img.naturalHeight));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.naturalWidth * scale);
        canvas.height = Math.round(img.naturalHeight * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("encode failed"))), "image/jpeg", 0.9);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("decode failed"));
      };
      img.src = url;
    });
  }

  async function loadPhoto(file) {
    say("reading photo");
    try {
      photoBlob = await downscale(file);
    } catch (_) {
      photoBlob = file; // the server may still be able to read it
    }
    if (preview.src) URL.revokeObjectURL(preview.src);
    preview.src = URL.createObjectURL(photoBlob);
    preview.hidden = false;
    $("preview-empty").hidden = true;
    say("photo ok");
  }

  for (const id of ["camera-input", "library-input"]) {
    $(id).addEventListener("change", (event) => {
      const file = event.target.files && event.target.files[0];
      event.target.value = ""; // allow picking the same file again
      if (file) loadPhoto(file);
    });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (sending) return;
    if (document.activeElement) document.activeElement.blur();
    if (!photoBlob) {
      say("no photo", true);
      return;
    }

    const data = new FormData(form);
    data.append("photo", photoBlob, "photo.jpg");
    sending = true;
    updateSendButton();
    say("sending");
    try {
      const result = await post("/user/api/submit", data);
      if (result.ok) {
        say(result.data.state.state === "loaded" ? "sent. waiting on enter" : "sent. printing");
      } else {
        say((result.data.message || "error " + result.status).toLowerCase(), true);
      }
    } catch (_) {
      say("no link", true);
    } finally {
      sending = false;
      updateSendButton();
    }
  });

  connectEvents({
    online(isOnline) {
      if (!isOnline) setStatus("offline");
    },
    state: latestState((snapshot) => setStatus(snapshot.state)),
  });
})();
