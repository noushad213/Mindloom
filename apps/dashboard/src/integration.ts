import type { PageStatus, SavedPage } from "./types";

export interface ExtensionExtractionResult {
  tabId: number;
  success: boolean;
  title?: string;
  url?: string;
  content?: string;
  error?: string;
}

export interface IngestPayload {
  client_event_id: string;
  url: string;
  title: string;
  text: string;
  meta: {
    description: null;
    og_image: null;
    favicon: null;
    lang: null;
    site_name: null;
    byline: null;
  };
  extraction: { status: "ok"; method: string; error_code: null; error_message: null };
  tab: { browser_tab_id: number; window_id: null; active: false };
  captured_at: string;
}

export interface BackendPage {
  id: string;
  canonical_url: string;
  title: string | null;
  domain: string | null;
  status: string;
  first_seen_at: string;
}

export function createIngestPayload(result: ExtensionExtractionResult): IngestPayload {
  if (!result.success || !result.url) {
    throw new Error(result.error || "The extension did not return readable page content.");
  }

  return {
    client_event_id: crypto.randomUUID(),
    url: result.url,
    title: result.title?.trim() || "Untitled page",
    text: result.content || "",
    meta: {
      description: null,
      og_image: null,
      favicon: null,
      lang: null,
      site_name: null,
      byline: null,
    },
    extraction: {
      status: "ok",
      method: "document.body.innerText",
      error_code: null,
      error_message: null,
    },
    tab: { browser_tab_id: result.tabId, window_id: null, active: false },
    captured_at: new Date().toISOString(),
  };
}

export function mapBackendPage(page: BackendPage): SavedPage {
  return {
    id: page.id,
    canonicalUrl: page.canonical_url,
    title: page.title || "Untitled page",
    sourceDomain: page.domain || new URL(page.canonical_url).hostname,
    status: page.status as PageStatus,
    capturedAt: page.first_seen_at,
  };
}
