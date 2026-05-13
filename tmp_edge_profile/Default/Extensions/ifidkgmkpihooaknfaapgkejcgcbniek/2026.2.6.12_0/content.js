"use strict";

(function() {
    // Lightweight ping to Service Worker.
    // Does NOT read storage. Does NOT parse logic.
    chrome.runtime.sendMessage({
        action: "APPLY_RULES_FOR_TAB",
        url: window.location.href
    }).catch(() => {
        // Silent fail (expected during extension updates)
    });
})();