import type { GraphEdge, GraphPage } from "../../types";

const colors = ["#1590a0", "#d49a32", "#9372c4", "#4a9b70", "#d47873", "#5683c2"];

export function pageCluster(page: GraphPage): string {
  return page.group_ids?.[0] || page.sourceDomain.toLowerCase() || "other";
}

export function clusterColor(key: string): string {
  let hash = 0;
  for (const char of key) hash = (hash * 31 + char.charCodeAt(0)) | 0;
  return colors[Math.abs(hash) % colors.length];
}

export function displayEdges(pages: GraphPage[], saved: GraphEdge[]): GraphEdge[] {
  const result = [...saved];
  const connected = new Set(saved.map((edge) => [edge.source, edge.target].sort().join(":")));
  const clusters = new Map<string, GraphPage[]>();
  for (const page of pages) {
    // A matching saved group is meaningful; otherwise only a shared domain is inferred.
    const key = page.group_ids?.[0] ? `group:${page.group_ids[0]}` : `domain:${page.sourceDomain.toLowerCase()}`;
    if (key === "domain:") continue;
    clusters.set(key, [...(clusters.get(key) || []), page]);
  }
  for (const [key, members] of clusters) {
    for (let i = 1; i < members.length; i++) {
      const source = members[i - 1].id;
      const target = members[i].id;
      const pair = [source, target].sort().join(":");
      if (connected.has(pair)) continue;
      connected.add(pair);
      result.push({
        id: `visual:${source}:${target}`, source, target,
        type: "related_to", label: key.startsWith("group:") ? "Same group" : "Same source",
        origin: "suggested", status: "suggested",
        evidence: key.startsWith("group:") ? "Shared workspace group" : `Shared source: ${members[i].sourceDomain}`,
      });
    }
  }
  return result;
}
