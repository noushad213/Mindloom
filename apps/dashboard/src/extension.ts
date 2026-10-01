import type { ExtensionExtractionResult } from "./integration";

interface ExtensionTab { id: number; title: string; url: string; active: boolean; status?: string }
interface ExtensionMessage {
  action: string;
  tab?: ExtensionTab;
  tabId?: number;
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
  retry(tabId: number): void;
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
  const lastRequestedUrlByTab = new Map<number, string>();

  const requestExtraction = (tab: ExtensionTab, force = false) => {
    if (tab.status && tab.status !== "complete") return;
    if (!Number.isInteger(tab.id) || !tab.url || (!force && lastRequestedUrlByTab.get(tab.id) === tab.url)) return;
    // Record before posting so bursts of TAB_UPDATED events cannot queue the same URL.
    lastRequestedUrlByTab.set(tab.id, tab.url);
    port.postMessage({ action: "EXTRACT_TABS", tabIds: [tab.id] });
  };

  port.onMessage.addListener((message) => {
    if (message.action === "INITIAL_TABS") {
      onReady();
      for (const tab of message.tabs || []) requestExtraction(tab);
    }
    if (message.action === "CONTENT_RESULTS") onResults(message.results || []);
    if ((message.action === "TAB_ADDED" || message.action === "TAB_UPDATED") && message.tab) {
      requestExtraction(message.tab);
    }
    if (message.action === "TAB_READY" && message.tab) requestExtraction(message.tab, true);
    if (message.action === "TAB_REMOVED" && Number.isInteger(message.tabId)) {
      lastRequestedUrlByTab.delete(message.tabId!);
    }
  });
  port.onDisconnect.addListener(() => {
    lastRequestedUrlByTab.clear();
    onDisconnect();
  });
  return {
    disconnect: () => port.disconnect(),
    retry: (tabId) => port.postMessage({ action: "EXTRACT_TABS", tabIds: [tabId] }),
  };
}
