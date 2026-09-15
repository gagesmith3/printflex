// Display screen: follows the server's state and drives the print animation.
(function () {
  "use strict";

  const { connectEvents, latestState, post } = window.PrintFlex;
  const $ = (id) => document.getElementById(id);
  const stage = $("stage");
  const printer = window.PrintAnimation.create(stage);
  const BOOT = [stage.dataset.program + " 0.9.3", "log off. nothing saved.", "listening for phone", ""];
  const WAITING = BOOT.concat(["waiting for photo "]);
  const KEY_ACTIONS = {
    Space: "start",
    Enter: "start",
    NumpadEnter: "start",
    KeyR: "replay",
    Escape: "reset",
    Backquote: "panic",
  };

  let settings = null;
  let shown = { bootId: null, run: -1 };

  function fitStage() {
    const scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.setProperty("--stage-scale", scale);
  }

  function tickClock() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    $("clock").textContent = now.toTimeString().slice(0, 8);
    $("decoy-date").textContent = pad(now.getMonth() + 1) + "/" + pad(now.getDate()) + "/" + now.getFullYear();
  }

  function render(snapshot) {
    $("decoy").hidden = !snapshot.panic;
    // Panic toggles and reconnects keep the same run; only real transitions redraw.
    if (snapshot.boot_id === shown.bootId && snapshot.run === shown.run) return;
    shown = { bootId: snapshot.boot_id, run: snapshot.run };

    const card = snapshot.job && snapshot.job.card;
    if (snapshot.state === "printing") {
      printer.play(snapshot.job, snapshot.phases, snapshot.elapsed);
    } else if (snapshot.state === "done") {
      printer.showDone(snapshot.job, snapshot.phases);
    } else if (snapshot.state === "loaded") {
      printer.idle(BOOT.concat(["> photo in  " + card.last + ", " + card.first, "[enter] to print "]));
    } else {
      printer.idle(WAITING);
    }
  }

  function applySettings(data) {
    settings = data;
    stage.style.setProperty("--scanlines", data.scanlines);
    $("connection").hidden = !data.show_connection_info;
  }

  document.addEventListener("keydown", (event) => {
    if (event.repeat) return;
    if (event.code === "KeyI") {
      if (settings) post("/server/api/settings", { show_connection_info: !settings.show_connection_info }).catch(() => {});
      return;
    }
    const action = KEY_ACTIONS[event.code];
    if (!action) return;
    event.preventDefault();
    post("/server/api/control/" + action).catch(() => {});
  });

  window.addEventListener("resize", fitStage);
  fitStage();
  tickClock();
  setInterval(tickClock, 1000);
  printer.idle(WAITING);

  connectEvents({
    online(isOnline) {
      $("link-status").textContent = isOnline ? "link ok" : "link down";
      $("link-status").classList.toggle("is-down", !isOnline);
    },
    settings: applySettings,
    state: latestState(render),
  });
})();
