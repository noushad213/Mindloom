import { createIngestPayload, mapBackendPage } from "./integration";
import type { BackendPage, ExtensionExtractionResult } from "./integration";
import type { SavedPage, Workspace } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

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
  const response = await request<{ items: BackendWorkspace[] }>("/api/v1/workspaces");
  if (response.items[0]) return response.items[0];
  return request<BackendWorkspace>("/api/v1/workspaces", {
    method: "POST",
    body: JSON.stringify({ name: "My Research", description: null, excluded_domains: [] }),
  });
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const response = await request<{ items: BackendWorkspace[] }>("/api/v1/workspaces");
  return response.items.map(({ id, name }) => ({ id, name }));
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
