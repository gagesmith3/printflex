// Shared helpers for talking to the PrintFlex server.
(function () {
  "use strict";

  const STATE_LABELS = {
    idle: "READY",
    loaded: "LOADED - WAITING FOR CUE",
    printing: "PRINTING",
    done: "PRINT COMPLETE",
    offline: "NO SIGNAL",
  };

  // Subscribe to server-sent events. handlers: { state(data), settings(data), online(isOnline) }
  function connectEvents(handlers) {
    let source = null;
    let retryTimer = null;

    function open() {
      source = new EventSource("/server/api/events");
      source.addEventListener("open", () => handlers.online && handlers.online(true));
      source.addEventListener("error", () => {
        if (handlers.online) handlers.online(false);
        // EventSource reconnects by itself unless the connection closed for good.
        if (source.readyState === EventSource.CLOSED) {
          clearTimeout(retryTimer);
          retryTimer = setTimeout(open, 2000);
        }
      });
      for (const name of ["state", "settings"]) {
        if (handlers[name]) {
          source.addEventListener(name, (event) => handlers[name](JSON.parse(event.data)));
        }
      }
    }

    open();
  }

  // Drop out-of-order state snapshots. Repeats still pass (a reconnect resends the current one),
  // so callbacks must handle the same snapshot twice. seq restarts whenever the server restarts.
  function latestState(callback) {
    let bootId = null;
    let seq = -1;
    return function (snapshot) {
      if (snapshot.boot_id === bootId && snapshot.seq < seq) return;
      bootId = snapshot.boot_id;
      seq = snapshot.seq;
      callback(snapshot);
    };
  }

  async function post(url, body) {
    const options = { method: "POST" };
    if (body instanceof FormData) {
      options.body = body;
    } else if (body !== undefined) {
      options.headers = { "Content-Type": "application/json" };
      options.body = JSON.stringify(body);
    }
    const response = await fetch(url, options);
    let data = {};
    try {
      data = await response.json();
    } catch (_) {
      // Non-JSON error page; the status code is enough.
    }
    return { ok: response.ok, status: response.status, data };
  }

  window.PrintFlex = { STATE_LABELS, connectEvents, latestState, post };
})();
