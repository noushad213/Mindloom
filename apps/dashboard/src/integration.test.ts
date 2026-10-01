import { describe, expect, it } from "vitest";
import { createIngestPayload, mapBackendPage } from "./integration";

describe("extension to backend contract", () => {
  it("converts successful extracted content into an ingest payload", () => {
    const payload = createIngestPayload({
      tabId: 42,
      success: true,
      title: "  Research article  ",
      url: "https://example.com/article",
      content: "Article text",
    });

    expect(payload).toMatchObject({
      url: "https://example.com/article",
      title: "Research article",
      text: "Article text",
      extraction: { status: "ok", method: "document.body.innerText" },
      tab: { browser_tab_id: 42, window_id: null, active: false },
    });
    expect(payload.client_event_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });

  it("maps backend snake_case page fields into dashboard fields", () => {
    expect(
      mapBackendPage({
        id: "page-1",
        canonical_url: "https://example.com/article",
        title: "Research article",
        domain: "example.com",
        status: "ready",
        first_seen_at: "2026-10-01T10:00:00Z",
      }),
    ).toEqual({
      id: "page-1",
      canonicalUrl: "https://example.com/article",
      title: "Research article",
      sourceDomain: "example.com",
      status: "ready",
      capturedAt: "2026-10-01T10:00:00Z",
    });
  });
});
