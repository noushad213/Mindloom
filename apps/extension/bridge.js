(() => {
  const ALLOWED_ORIGINS = new Set([
    "http://localhost:5173",
    "http://127.0.0.1:5173"
  ]);

  const UUID_PATTERN =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  window.addEventListener("message", (event) => {
    if (event.source !== window) return;
    if (!ALLOWED_ORIGINS.has(event.origin)) return;

    const message = event.data;

    if (!message || typeof message !== "object") return;

    if (message.type === "MINDLOOM_START_TRACKING") {
      if (
        typeof message.workspaceId !== "string" ||
        !UUID_PATTERN.test(message.workspaceId)
      ) {
        console.error("Mindloom: Invalid workspace ID.");
        return;
      }
    } else if (message.type !== "MINDLOOM_STOP_TRACKING") {
      return;
    }

    chrome.runtime.sendMessage(
      {
        type: message.type,
        workspaceId: message.workspaceId
      },
      (response) => {
        if (chrome.runtime.lastError) {
          console.error(
            "Mindloom bridge error:",
            chrome.runtime.lastError.message
          );
          return;
        }

        console.log("Mindloom extension response:", response);

        // Notify the React page that the background script responded.
        window.postMessage(
          {
            type: "MINDLOOM_EXTENSION_RESPONSE",
            requestType: message.type,
            response
          },
          window.location.origin
        );
      }
    );
  });
})();
