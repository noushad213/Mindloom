import { createIngestPayload, mapBackendPage } from "./integration";
import type { BackendPage, ExtensionExtractionResult } from "./integration";
import type { EdgeType, GraphEdge, GraphSnapshot, SavedPage, Workspace } from "./types";
const API_BASE_URL = (import.meta.env.VITE_API_URL || "https://b82wq2xh-8000.inc1.devtunnels.ms").replace(/\/$/, "");

export function shouldUseFixtures(value: string | undefined): boolean {
  return value?.toLowerCase() === "true";
}

interface BackendWorkspace extends Workspace {
  page_count: number;
}

const pendingReads = new Map<string, Promise<unknown>>();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const readKey = !init || init.method === "GET" ? path : null;
  if (readKey && pendingReads.has(readKey)) return pendingReads.get(readKey) as Promise<T>;
  const pending = (async () => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { error?: { message?: string } } | null;
      throw new Error(body?.error?.message || `Mindloom API returned ${response.status}.`);
    }
    return response.json() as Promise<T>;
  })();
  if (readKey) {
    pendingReads.set(readKey, pending);
    void pending.finally(() => pendingReads.delete(readKey)).catch(() => {});
  }
  return pending;
}

export async function getInitialWorkspaces(): Promise<{ initial: Workspace; all: Workspace[] }> {
  const response = await request<{ items: BackendWorkspace[] }>("/api/v1/workspaces");
  if (response.items.length > 0) {
    const all = response.items.map(({ id, name }) => ({ id, name }));
    return { initial: all[0], all };
  }
  const initial = await request<BackendWorkspace>("/api/v1/workspaces", {
    method: "POST",
    body: JSON.stringify({ name: "My Research", description: null, excluded_domains: [] }),
  });
  const mapped = { id: initial.id, name: initial.name };
  return { initial: mapped, all: [mapped] };
}

export async function listPages(workspaceId: string): Promise<SavedPage[]> {
  const response = await request<{ items: BackendPage[] }>(
    `/api/v1/workspaces/${workspaceId}/pages`,
  );
  return response.items.map(mapBackendPage);
}

export async function ingestExtraction(
  workspaceId: string,
  result: ExtensionExtractionResult,
): Promise<SavedPage> {
  const response = await request<{ page: BackendPage }>(
    `/api/v1/workspaces/${workspaceId}/pages`,
    { method: "POST", body: JSON.stringify(createIngestPayload(result)) },
  );
  return mapBackendPage(response.page);
}

export async function fetchGraphSnapshot(workspaceId: string): Promise<GraphSnapshot> {
  interface RawGraphSnapshot {
    workspace: { id: string; name: string };
    pages: Array<{
      id: string;
      canonical_url: string;
      title: string | null;
      domain: string | null;
      status: string;
      first_seen_at: string;
      pos: { x: number; y: number } | null;
      summary: string | null;
      importance: number | null;
      tab_open?: boolean;
      group_ids?: string[];
    }>;
    edges: GraphEdge[];
    seq?: number;
  }

  const res = await request<RawGraphSnapshot>(`/api/v1/workspaces/${workspaceId}/graph`);
  return {
    workspace: { id: res.workspace.id, name: res.workspace.name },
    pages: res.pages.map((p) => ({
      id: p.id,
      canonicalUrl: p.canonical_url,
      title: p.title || "Untitled page",
      sourceDomain: p.domain || (p.canonical_url ? new URL(p.canonical_url).hostname : ""),
      status: p.status as SavedPage["status"],
      capturedAt: p.first_seen_at,
      pos: p.pos,
      summary: p.summary,
      importance: p.importance,
      tabOpen: p.tab_open,
      group_ids: p.group_ids,
    })),
    edges: res.edges,
    seq: res.seq,
  };
}

export function workspaceSocketUrl(workspaceId: string): string {
  const url = new URL(API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/workspaces/${encodeURIComponent(workspaceId)}`;
  url.search = "";
  return url.toString();
}

export async function createEdge(
  workspaceId: string,
  payload: { source: string; target: string; type: EdgeType; label?: string | null },
): Promise<GraphEdge> {
  return request<GraphEdge>(`/api/v1/workspaces/${workspaceId}/edges`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteEdge(edgeId: string): Promise<void> {
  await fetch(`${API_BASE_URL}/api/v1/edges/${edgeId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
}

export async function updatePositions(
  workspaceId: string,
  positions: Array<{ id: string; x: number; y: number }>,
): Promise<void> {
  if (positions.length === 0) return;
  await request<{ updated: number }>(`/api/v1/workspaces/${workspaceId}/pages/positions`, {
    method: "PATCH",
    body: JSON.stringify({ positions }),
  });
}
