import { describe, expect, it } from "vitest";
import { clusterColor, displayEdges, pageCluster } from "./graphPresentation";
import type { GraphPage } from "../../types";

const page = (id: string, domain: string): GraphPage => ({
  id, canonicalUrl: `https://${domain}/${id}`, title: id, sourceDomain: domain,
  status: "ready", capturedAt: "2026-01-01T00:00:00Z",
});

describe("graph presentation", () => {
  it("links matching sources with a labeled, evidenced view-only relationship", () => {
    const edges = displayEdges([page("a", "example.com"), page("b", "example.com")], []);
    expect(edges).toMatchObject([{ label: "Same source", evidence: "Shared source: example.com" }]);
    expect(edges[0].id).toMatch(/^visual:/);
  });

  it("does not duplicate a saved relationship", () => {
    const saved = { id: "1", source: "a", target: "b", type: "supports" as const,
      label: null, origin: "manual" as const, status: "accepted" as const };
    expect(displayEdges([page("a", "example.com"), page("b", "example.com")], [saved])).toEqual([saved]);
  });

  it("assigns the same color to pages in a saved group", () => {
    const a = { ...page("a", "one.com"), group_ids: ["group-1"] };
    const b = { ...page("b", "two.com"), group_ids: ["group-1"] };
    expect(clusterColor(pageCluster(a))).toBe(clusterColor(pageCluster(b)));
  });
});
