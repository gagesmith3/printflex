// Phone capture page: take a photo, enter a name, send it to the printer.
(function () {
  "use strict";

  const { STATE_LABELS, connectEvents, latestState, post } = window.PrintFlex;
  const MAX_EDGE = 1600;

  const $ = (id) => document.getElementById(id);
  const form = $("capture-form");
  const preview = $("preview");
  const sendButton = $("send");
  const message = $("message");

  let photoBlob = null;
  let printerState = "offline";
  let sending = false;

  function showMessage(text, kind) {
    message.textContent = text;
    message.className = "message" + (kind ? " message--" + kind : "");
  }

  function updateSendButton() {
    const busy = printerState === "printing" || printerState === "done";
    sendButton.disabled = sending || busy;
    sendButton.textContent = sending ? "TRANSMITTING..." : busy ? "PRINTER BUSY" : ">> SEND TO PRINTER <<";
  }

  function setStatus(state, detail) {
    printerState = state;
    $("status").dataset.state = state;
    $("status-text").textContent = STATE_LABELS[state] + (detail ? " : " + detail : "");
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
    showMessage("PROCESSING IMAGE...");
    try {
      photoBlob = await downscale(file);
    } catch (_) {
      photoBlob = file; // the server may still be able to read it
    }
    if (preview.src) URL.revokeObjectURL(preview.src);
    preview.src = URL.createObjectURL(photoBlob);
    preview.hidden = false;
    $("preview-empty").hidden = true;
    showMessage("IMAGE CAPTURED", "ok");
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
      showMessage("TAKE A PHOTO FIRST", "error");
      return;
    }

    const data = new FormData(form);
    data.append("photo", photoBlob, "photo.jpg");
    sending = true;
    updateSendButton();
    showMessage("TRANSMITTING...");
    try {
      const result = await post("/user/api/submit", data);
      if (result.ok) {
        const loaded = result.data.state.state === "loaded";
        showMessage(loaded ? "LOADED. WAITING FOR CUE." : "RECEIVED. PRINTING...", "ok");
      } else {
        showMessage(result.data.message || "ERROR " + result.status, "error");
      }
    } catch (_) {
      showMessage("NO CONNECTION TO PRINTER", "error");
    } finally {
      sending = false;
      updateSendButton();
    }
  });

  connectEvents({
    online(isOnline) {
      if (!isOnline) setStatus("offline");
    },
    state: latestState((snapshot) => {
      const card = snapshot.job && snapshot.job.card;
      setStatus(snapshot.state, card ? card.last + ", " + card.first : "");
    }),
  });
})();
