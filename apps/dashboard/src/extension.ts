export interface ExtensionConnection {
  disconnect(): void;
}

export function connectToExtension(
  workspaceId: string,
  onReady: () => void,
  onDisconnect: () => void,
): ExtensionConnection {
  let connected = false;
  const timeout = window.setTimeout(() => {
    if (!connected) onDisconnect();
  }, 5000);
  const listener = (event: MessageEvent) => {
    if (event.source !== window) return;
    const message = event.data;
    if (
      message?.type === "MINDLOOM_EXTENSION_RESPONSE" &&
      message.requestType === "MINDLOOM_START_TRACKING"
    ) {
      connected = true;
      window.clearTimeout(timeout);
      if (message.response?.success) {
        onReady();
      } else {
        console.error("Extension tracking failed to start:", message.response?.message);
        onDisconnect();
      }
    }
  };

  window.addEventListener("message", listener);
  window.postMessage({ type: "MINDLOOM_START_TRACKING", workspaceId }, window.location.origin);

  return {
    disconnect: () => {
      window.clearTimeout(timeout);
      window.removeEventListener("message", listener);
      window.postMessage({ type: "MINDLOOM_STOP_TRACKING" }, window.location.origin);
    }
  };
}
