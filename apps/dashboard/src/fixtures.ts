// DRAFT — pending Member 3 API schema
// Fixture data for building and testing the dashboard before the real API.
// Field names and structure will change once the OpenAPI schema is published.

import type { SavedPage, CollectionEvent, Workspace } from "./types";

export const FIXTURE_WORKSPACES: Workspace[] = [
  { id: "ws-1", name: "ML Research" },
  { id: "ws-2", name: "Systems Design" },
  { id: "ws-3", name: "HCI Papers" },
];

export const FIXTURE_SAVED_PAGES: SavedPage[] = [
  {
    id: "page-1",
    canonicalUrl: "https://arxiv.org/abs/1706.03762",
    title: "Attention Is All You Need — Transformer Architecture",
    sourceDomain: "arxiv.org",
    status: "captured",
    capturedAt: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
  },
  {
    id: "page-2",
    canonicalUrl: "https://www.nature.com/articles/s41586-021-03819-2",
    title: "Highly accurate protein structure prediction with AlphaFold",
    sourceDomain: "nature.com",
    status: "processing",
    capturedAt: new Date(Date.now() - 30 * 1000).toISOString(),
  },
  {
    id: "page-3",
    canonicalUrl: "https://github.com/Avi-141/weft",
    title: "Weft — Visual Browser Tab Manager",
    sourceDomain: "github.com",
    status: "captured",
    capturedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
  {
    id: "page-4",
    canonicalUrl: "https://dl.acm.org/doi/10.1145/3491102.3517607",
    title: "Sensemaking in the Age of AI: How People Build Mental Models",
    sourceDomain: "dl.acm.org",
    status: "queued",
    capturedAt: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
  },
];

export const FIXTURE_COLLECTION_EVENTS: CollectionEvent[] = [
  {
    eventId: "evt-1",
    tabId: 101,
    url: "chrome://extensions",
    title: "Extensions",
    timestamp: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
    status: "failed",
    errorCode: "ineligible_scheme",
    errorDetail: "Browser internal pages are not accessible to extensions.",
  },
  {
    eventId: "evt-2",
    tabId: 102,
    url: "https://mail.google.com/mail/u/0/",
    title: "Gmail",
    timestamp: new Date(Date.now() - 1 * 60 * 1000).toISOString(),
    status: "failed",
    errorCode: "permission_denied",
    errorDetail:
      "Content script injection blocked. User may need to grant host permission.",
  },
];

/** Human-readable error messages keyed by error code. */
export const ERROR_MESSAGES: Record<string, { text: string; action: "dismiss" | "retry" }> = {
  ineligible_scheme: {
    text: "Browser internal pages cannot be captured.",
    action: "dismiss",
  },
  permission_denied: {
    text: "This site blocked content access.",
    action: "retry",
  },
  network_error: {
    text: "Could not reach this page.",
    action: "retry",
  },
  extraction_failed: {
    text: "Page content could not be read.",
    action: "retry",
  },
};
