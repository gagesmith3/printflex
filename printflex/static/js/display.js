// Display screen: follows the server's state and drives the print animation.
(function () {
  "use strict";

  const { connectEvents, latestState, post } = window.PrintFlex;
  const $ = (id) => document.getElementById(id);
  const stage = $("stage");
  const printer = window.PrintAnimation.create(stage);
  const KEY_ACTIONS = { " ": "start", Enter: "start", r: "replay", R: "replay", Escape: "reset" };

  let settings = null;
  let shown = { bootId: null, seq: -1 };

  function fitStage() {
    const scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    stage.style.setProperty("--stage-scale", scale);
  }

  function tickClock() {
    $("clock").textContent = new Date().toTimeString().slice(0, 8);
  }

  function showScreen(name) {
    $("screen-idle").hidden = name !== "idle";
    $("screen-job").hidden = name !== "job";
  }

  function render(snapshot) {
    // A reconnect resends the current snapshot; don't restart what's already on screen.
    if (snapshot.boot_id === shown.bootId && snapshot.seq === shown.seq) return;
    shown = { bootId: snapshot.boot_id, seq: snapshot.seq };

    if (snapshot.state === "printing") {
      showScreen("job");
      printer.play(snapshot.job, snapshot.phases, snapshot.elapsed);
    } else if (snapshot.state === "done") {
      showScreen("job");
      printer.showDone(snapshot.job);
    } else {
      const loaded = snapshot.state === "loaded";
      printer.stop();
      showScreen("idle");
      $("ready-text").classList.toggle("is-loaded", loaded);
      $("ready-label").textContent = loaded ? " DATA RECEIVED" : " READY";
      $("ready-sub").textContent = loaded ? "PRESS ENTER TO PRINT" : "AWAITING TRANSMISSION";
    }
  }

  function applySettings(data) {
    settings = data;
    stage.style.setProperty("--scanlines", data.scanlines);
    $("connection").hidden = !data.show_connection_info;
    $("mode-label").textContent = data.mode === "cue" ? "CUE" : "AUTO";
  }

  document.addEventListener("keydown", (event) => {
    if (event.repeat) return;
    if (event.key === "i" || event.key === "I") {
      if (settings) post("/server/api/settings", { show_connection_info: !settings.show_connection_info }).catch(() => {});
      return;
    }
    const action = KEY_ACTIONS[event.key];
    if (action) {
      event.preventDefault();
      post("/server/api/control/" + action).catch(() => {});
    }
  });

  window.addEventListener("resize", fitStage);
  fitStage();
  tickClock();
  setInterval(tickClock, 1000);

  connectEvents({
    online(isOnline) {
      $("link-status").textContent = isOnline ? "LINK OK" : "NO LINK";
      $("link-status").classList.toggle("red", !isOnline);
    },
    settings: applySettings,
    state: latestState(render),
  });
})();
