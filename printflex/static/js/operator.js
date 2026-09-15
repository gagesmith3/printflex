// Crew panel: trigger mode, START / REPLAY / RESET, timing and display settings.
(function () {
  "use strict";

  const { STATE_LABELS, connectEvents, latestState, post } = window.PrintFlex;
  const $ = (id) => document.getElementById(id);
  const message = $("message");

  let settings = null;
  let snapshot = null;

  function showMessage(text, kind) {
    message.textContent = text;
    message.className = "message" + (kind ? " message--" + kind : "");
  }

  function renderState() {
    const state = snapshot ? snapshot.state : "offline";
    const card = snapshot && snapshot.job && snapshot.job.card;
    $("status").dataset.state = state;
    $("status-text").textContent = STATE_LABELS[state] + (card ? " : " + card.last + ", " + card.first : "");
    $("job-line").textContent = "LAST JOB: " + (snapshot && snapshot.last_job ? snapshot.last_job.name : "NONE");
    $("btn-start").disabled = state !== "loaded";
    $("btn-replay").disabled = !(snapshot && snapshot.last_job);
    $("btn-reset").disabled = !snapshot;
  }

  // Don't overwrite a field the crew member is typing in.
  function setValue(input, value) {
    if (document.activeElement !== input) input.value = value;
  }

  function renderSettings() {
    if (!settings) return;
    for (const button of document.querySelectorAll(".mode__option")) {
      button.setAttribute("aria-checked", String(button.dataset.mode === settings.mode));
    }
    $("mode-hint").textContent =
      settings.mode === "cue" ? "PHOTOS LOAD AND WAIT FOR START." : "PHOTOS PRINT AS SOON AS THEY ARRIVE.";
    setValue($("speed"), settings.speed);
    $("speed-value").textContent = settings.speed.toFixed(1) + "X";
    for (const input of document.querySelectorAll("[data-phase]")) {
      setValue(input, settings.phases[input.dataset.phase]);
    }
    setValue($("hold"), settings.hold_seconds);
    setValue($("scanlines"), settings.scanlines);
    $("scanlines-value").textContent = Math.round(settings.scanlines * 100) + "%";
    $("show-connection").checked = settings.show_connection_info;

    const seconds = Object.values(settings.phases).reduce((sum, value) => sum + value, 0) / settings.speed;
    const hold = settings.hold_seconds > 0 ? " + " + settings.hold_seconds + "S HOLD" : " + HOLD UNTIL RESET";
    $("total").textContent = seconds.toFixed(1) + "S" + hold;
  }

  async function saveSettings(changes) {
    try {
      const result = await post("/server/api/settings", changes);
      if (result.ok) {
        settings = result.data;
        showMessage("SAVED", "ok");
      } else {
        showMessage(result.data.message || "SAVE FAILED", "error");
      }
    } catch (_) {
      showMessage("NO CONNECTION", "error");
    }
    renderSettings();
  }

  // Returns null for a blank or non-numeric field so it isn't saved as 0.
  function numberFrom(input) {
    const value = input.value.trim() === "" ? NaN : Number(input.value);
    return Number.isFinite(value) ? value : null;
  }

  function saveNumber(input, toChanges) {
    const value = numberFrom(input);
    if (value === null) {
      input.value = "";
      renderSettings();
      return;
    }
    saveSettings(toChanges(value));
  }

  for (const button of document.querySelectorAll(".mode__option")) {
    button.addEventListener("click", () => saveSettings({ mode: button.dataset.mode }));
  }

  $("speed").addEventListener("input", () => {
    $("speed-value").textContent = Number($("speed").value).toFixed(1) + "X";
  });
  $("speed").addEventListener("change", () => saveNumber($("speed"), (speed) => ({ speed })));

  $("scanlines").addEventListener("input", () => {
    $("scanlines-value").textContent = Math.round(Number($("scanlines").value) * 100) + "%";
  });
  $("scanlines").addEventListener("change", () => saveNumber($("scanlines"), (scanlines) => ({ scanlines })));

  for (const input of document.querySelectorAll("[data-phase]")) {
    input.addEventListener("change", () =>
      saveNumber(input, (seconds) => ({ phases: { [input.dataset.phase]: seconds } }))
    );
  }
  $("hold").addEventListener("change", () => saveNumber($("hold"), (hold_seconds) => ({ hold_seconds })));
  $("show-connection").addEventListener("change", () =>
    saveSettings({ show_connection_info: $("show-connection").checked })
  );

  for (const button of document.querySelectorAll("[data-action]")) {
    button.addEventListener("click", async () => {
      try {
        const result = await post("/server/api/control/" + button.dataset.action);
        if (result.ok) showMessage(button.textContent + " OK", "ok");
        else showMessage(result.data.message || "ERROR " + result.status, "error");
      } catch (_) {
        showMessage("NO CONNECTION", "error");
      }
    });
  }

  connectEvents({
    online(isOnline) {
      if (!isOnline) {
        snapshot = null;
        renderState();
      }
    },
    settings(data) {
      settings = data;
      renderSettings();
    },
    state: latestState((data) => {
      snapshot = data;
      renderState();
    }),
  });
  renderState();
})();
