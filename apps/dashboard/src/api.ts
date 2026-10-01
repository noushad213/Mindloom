import { createIngestPayload, mapBackendPage } from "./integration";
import type { BackendPage, ExtensionExtractionResult } from "./integration";
import type { EdgeType, GraphEdge, GraphPage, GraphSnapshot, SavedPage, Workspace } from "./types";
import { FIXTURE_SAVED_PAGES, FIXTURE_WORKSPACES } from "./fixtures";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
export function shouldUseFixtures(value: string | undefined): boolean {
  return value?.toLowerCase() === "true";
}
export const isFixtureMode = shouldUseFixtures(import.meta.env.VITE_USE_FIXTURES);

interface BackendWorkspace extends Workspace {
  page_count: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: { message?: string } } | null;
    throw new Error(body?.error?.message || `Mindloom API returned ${response.status}.`);
  }
  return response.json() as Promise<T>;
}

export async function loadOrCreateWorkspace(): Promise<Workspace> {
  if (isFixtureMode) return { ...FIXTURE_WORKSPACES[0] };
  const response = await request<{ items: BackendWorkspace[] }>("/api/v1/workspaces");
  if (response.items[0]) return response.items[0];
  return request<BackendWorkspace>("/api/v1/workspaces", {
    method: "POST",
    body: JSON.stringify({ name: "My Research", description: null, excluded_domains: [] }),
  });
}

export async function listWorkspaces(): Promise<Workspace[]> {
  if (isFixtureMode) return FIXTURE_WORKSPACES.map((workspace) => ({ ...workspace }));
  const response = await request<{ items: BackendWorkspace[] }>("/api/v1/workspaces");
  return response.items.map(({ id, name }) => ({ id, name }));
}

export async function listPages(workspaceId: string): Promise<SavedPage[]> {
  if (isFixtureMode) {
    return workspaceId === FIXTURE_WORKSPACES[0].id
      ? FIXTURE_SAVED_PAGES.map((page) => ({ ...page }))
      : [];
  }
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
  if (isFixtureMode) {
    const pages: GraphPage[] = FIXTURE_SAVED_PAGES.map((p, i) => ({
      ...p,
      pos: { x: 80 + (i % 3) * 280, y: 100 + Math.floor(i / 3) * 200 },
      summary: null,
      importance: 3,
    }));
    const edges: GraphEdge[] = [
      {
        id: "edge-fixture-1",
        source: pages[0]?.id || "page-1",
        target: pages[1]?.id || "page-2",
        type: "related_to",
        label: "AI Architecture",
        origin: "manual",
        status: "accepted",
      },
    ];
    return {
      workspace: { ...FIXTURE_WORKSPACES[0] },
      pages,
      edges,
    };
  }

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

export async function createEdge(
  workspaceId: string,
  payload: { source: string; target: string; type: EdgeType; label?: string | null },
): Promise<GraphEdge> {
  if (isFixtureMode) {
    return {
      id: `edge-${crypto.randomUUID()}`,
      source: payload.source,
      target: payload.target,
      type: payload.type,
      label: payload.label || null,
      origin: "manual",
      status: "accepted",
    };
  }

  return request<GraphEdge>(`/api/v1/workspaces/${workspaceId}/edges`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteEdge(edgeId: string): Promise<void> {
  if (isFixtureMode) return;
  await fetch(`${API_BASE_URL}/api/v1/edges/${edgeId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
}

export async function updatePositions(
  workspaceId: string,
  positions: Array<{ id: string; x: number; y: number }>,
): Promise<void> {
  if (isFixtureMode || positions.length === 0) return;
  await request<{ updated: number }>(`/api/v1/workspaces/${workspaceId}/pages/positions`, {
    method: "PATCH",
    body: JSON.stringify({ positions }),
  });
}
