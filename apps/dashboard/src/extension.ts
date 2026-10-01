import type { ExtensionExtractionResult } from "./integration";

interface ExtensionTab { id: number; title: string; url: string; active: boolean }
interface ExtensionMessage {
  action: string;
  tabs?: ExtensionTab[];
  results?: ExtensionExtractionResult[];
}
interface ExtensionPort {
  postMessage(message: object): void;
  disconnect(): void;
  onMessage: { addListener(listener: (message: ExtensionMessage) => void): void };
  onDisconnect: { addListener(listener: () => void): void };
}
interface ChromeRuntime {
  runtime?: { connect(extensionId: string, options: { name: string }): ExtensionPort; lastError?: unknown };
}

export interface ExtensionConnection {
  disconnect(): void;
}

export function connectToExtension(
  extensionId: string,
  onResults: (results: ExtensionExtractionResult[]) => void,
  onReady: () => void,
  onDisconnect: () => void,
): ExtensionConnection {
  const runtime = (window as Window & { chrome?: ChromeRuntime }).chrome?.runtime;
  if (!extensionId || !runtime) throw new Error("Mindloom extension is not configured.");

  const port = runtime.connect(extensionId, { name: "mindloom-dashboard" });
  port.onMessage.addListener((message) => {
    if (message.action === "INITIAL_TABS") {
      const tabIds = (message.tabs || []).map((tab) => tab.id);
      onReady();
      if (tabIds.length) port.postMessage({ action: "EXTRACT_TABS", tabIds });
    }
    if (message.action === "CONTENT_RESULTS") onResults(message.results || []);
  });
  port.onDisconnect.addListener(onDisconnect);
  return { disconnect: () => port.disconnect() };
}
