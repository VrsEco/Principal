(function () {
  "use strict";

  const HEARTBEAT_INTERVAL_MS = 60000;
  let timer = null;

  async function sendHeartbeat() {
    if (document.visibilityState !== "visible") return;
    try {
      await fetch("/api/presence/heartbeat", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: "{}",
        keepalive: true,
      });
    } catch (_) {
      // Presença é observabilidade: falhas não podem bloquear a navegação.
    }
  }

  function start() {
    if (timer) window.clearInterval(timer);
    sendHeartbeat();
    timer = window.setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") sendHeartbeat();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
