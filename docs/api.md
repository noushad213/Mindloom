# Mindloom — API Reference (v1)

Base URL: `http://localhost:8000/api/v1` · JSON everywhere · UTF-8 · timestamps ISO-8601 UTC.
Interactive docs are auto-generated at `/docs` (FastAPI). **This file is the contract**; Member 3 keeps it in sync with the code and publishes fixtures in `docs/fixtures/`.

## 0. Conventions

**Auth (hackathon):** none for the owner's local session. Shared access uses `?share=<token>` or header `X-Share-Token: <token>` (role `view` = GET only). Extension sends `X-Client: mindloom-extension/<version>`.

**Error envelope** (all non-2xx):
```json
{"error": {"code": "validation_error", "message": "url is required", "details": {"field": "url"}}}
```
Codes: `validation_error` (422), `not_found` (404), `conflict` (409), `excluded_domain` (422), `payload_too_large` (413), `forbidden` (403), `rate_limited` (429), `internal_error` (500).

**Pagination:** `?limit=50&offset=0` → `{"items":[...],"total":123,"limit":50,"offset":0}`.

**Enums**
- Page.status: `discovered|extracting|extracted|processing|ready|extraction_failed|processing_failed`
- Edge.type: `related_to|source_of|answers|supports|references|navigated_to|duplicate_of|custom`
- Edge.origin: `suggested|manual` · Edge.status: `suggested|accepted|rejected`
- Extraction error codes: `restricted_url|excluded_domain|no_permission|injection_blocked|empty_content|pdf_unsupported|timeout`

**Object shapes**
```json
// Page
{"id":"p_1","workspace_id":"w_1","url":"https://...","canonical_url":"https://...","title":"...",
 "domain":"nature.com","favicon_url":null,"og_image_url":null,"summary":"...","keywords":["a","b"],
 "status":"ready","error_code":null,"error_message":null,"pos":{"x":120.5,"y":80},
 "importance":3,"tags":[{"id":"t_1","name":"key","color":"#f59e0b"}],"group_ids":["g_1"],
 "tab_open":true,"first_seen_at":"...","last_seen_at":"...","updated_at":"..."}
// Edge
{"id":"e_1","source":"p_1","target":"p_2","type":"answers","label":null,"origin":"suggested",
 "status":"suggested","confidence":0.62,"evidence":{"method":"...","shared_keywords":[],"snippets":[]},
 "updated_at":"..."}
// Group
{"id":"g_1","name":"Clinical AI","category":"topic","color":"#6366f1","origin":"suggested",
 "status":"suggested","keywords":["triage"],"page_ids":["p_1","p_2"],"collapsed":false}
// Note
{"id":"n_1","target_type":"page","target_id":"p_1","kind":"highlight","body":"check this","quote":"...","author":"Asha","created_at":"...","updated_at":"..."}
```

---

## 1. Health
| Feature | Request | Response |
|---|---|---|
| Health check | `GET /health` | `200 {"status":"ok","version":"0.1.0","db":"ok"}` |

## 2. Workspaces
| Feature | Request | Response |
|---|---|---|
| Create | `POST /workspaces` `{"name":"AI in healthcare","description":"","excluded_domains":["mail.google.com"]}` | `201 Workspace` |
| List | `GET /workspaces?include_archived=false` | `200 {"items":[Workspace]}` with `page_count`, `updated_at` |
| Get | `GET /workspaces/{id}` | `200 Workspace` |
| Update (rename, exclusions, settings, view_state, tracking) | `PATCH /workspaces/{id}` `{"name":"...","excluded_domains":[...],"settings":{...},"view_state":{...},"tracking":true}` | `200 Workspace` |
| Delete (hard) | `DELETE /workspaces/{id}` | `204` |
| Full graph snapshot (resume) | `GET /workspaces/{id}/graph` | `200 {"workspace":Workspace,"pages":[Page],"edges":[Edge],"groups":[Group],"notes":[Note],"tags":[Tag],"seq":42}` (excludes rejected edges unless `?include_rejected=true`) |

Workspace: `{"id","name","description","excluded_domains","settings","view_state","tracking","page_count","created_at","updated_at"}`

## 3. Ingestion (extension → backend)
| Feature | Request | Response |
|---|---|---|
| Ingest one page | `POST /workspaces/{id}/pages` | `201` new / `200` existing: `{"page":Page,"tab_session":TabSession,"created":true,"duplicate_of":null,"job":"queued"}` |
| Ingest batch | `POST /workspaces/{id}/pages/batch` `{"items":[IngestPayload,...]}` (max 25) | `200 {"results":[{"index":0,"ok":true,"page_id":"p_1"},{"index":1,"ok":false,"error":{...}}]}` |

**IngestPayload**
```json
{
  "client_event_id": "c2f1-...-uuid",
  "url": "https://www.nature.com/articles/xyz?utm_source=x",
  "title": "AI triage in emergency care",
  "text": "cleaned article text...",
  "meta": {"description":"...","og_image":"https://...","favicon":"https://...","lang":"en","site_name":"Nature","byline":"A. Author"},
  "extraction": {"status":"ok","method":"readability","error_code":null,"error_message":null},
  "tab": {"browser_tab_id":123,"window_id":1,"active":false},
  "captured_at": "2026-10-01T10:00:00Z"
}
```
- `client_event_id` makes retries idempotent (same id → same response body with `200`, no duplicate).
- `extraction.status="failed"` → `text` may be empty; backend stores page with `status=extraction_failed` + `error_code`.
- Limits: `text` ≤ 100,000 chars (server truncates to `MAX_TEXT_CHARS`), body ≤ 2 MB → else `413`.
- Excluded domain → `422 excluded_domain`.

| Feature | Request | Response |
|---|---|---|
| Tab lifecycle event (open/navigate/close, no content) | `POST /workspaces/{id}/tab-events` `{"event":"created|updated|activated|removed","browser_tab_id":123,"url":"...","title":"...","active":true}` | `202 {"ok":true}` (emits `page.discovered` for new URLs; `removed` sets tab_session closed) |
| List tab sessions | `GET /workspaces/{id}/tab-sessions?state=open` | `200 {"items":[TabSession]}` |
| Close a tab session | `PATCH /tab-sessions/{id}` `{"state":"closed"}` | `200 TabSession` |

TabSession: `{"id","page_id","browser_tab_id","state","active","opened_at","last_seen_at","closed_at"}`

## 4. Pages (nodes)
| Feature | Request | Response |
|---|---|---|
| List | `GET /workspaces/{id}/pages?status=&domain=&tag=&group_id=&sort=recent&limit=&offset=` | `200 {items:[Page],total,...}` |
| Get (with text) | `GET /pages/{id}?include_text=true` | `200 Page` + `text` |
| Get within workspace | `GET /workspaces/{id}/pages/{page_id}?include_text=true` | `200 Page` + optional `text`; `404` if the page belongs to another workspace |
| Update (move, title, importance) | `PATCH /pages/{id}` `{"pos":{"x":1,"y":2},"title":"...","importance":4}` | `200 Page` |
| Bulk move (drag end) | `PATCH /workspaces/{id}/pages/positions` `{"positions":[{"id":"p_1","x":1,"y":2}]}` | `200 {"updated":1}` |
| Manually add by URL | `POST /workspaces/{id}/pages/manual` `{"url":"https://..."}` | `201 Page` (status `discovered`; backend fetches server-side via Trafilatura if reachable) |
| Delete from workspace | `DELETE /pages/{id}?block=false` | `204` |
| Reprocess | `POST /pages/{id}/reprocess` | `202 {"job":"queued"}` |

## 5. Edges
| Feature | Request | Response |
|---|---|---|
| List | `GET /workspaces/{id}/edges?origin=&status=&page_id=` | `200 {items:[Edge]}` |
| Create manual | `POST /workspaces/{id}/edges` `{"source":"p_1","target":"p_2","type":"answers","label":null}` | `201 Edge` (`origin=manual,status=accepted`); `409` if same pair+type exists |
| Edit (type/label/direction) | `PATCH /edges/{id}` `{"type":"supports","label":null,"swap_direction":false}` | `200 Edge` (editing a suggested edge → `status=accepted`) |
| Accept suggestion | `POST /edges/{id}/accept` | `200 Edge` |
| Delete / reject | `DELETE /edges/{id}` | `204` — manual: row deleted; suggested: marked `rejected` (tombstone) |
| List rejected | `GET /workspaces/{id}/edges?status=rejected` | `200 {items:[Edge]}` |
| Restore rejected | `POST /edges/{id}/restore` | `204` (tombstone removed) |

## 6. Groups
| Feature | Request | Response |
|---|---|---|
| List | `GET /workspaces/{id}/groups` | `200 {items:[Group]}` |
| Create | `POST /workspaces/{id}/groups` `{"name":"Sources","category":"source","color":"#10b981","page_ids":["p_1"]}` | `201 Group` |
| Update | `PATCH /groups/{id}` `{"name":"...","category":"topic","color":"#...","collapsed":true}` | `200 Group` (promotes to `origin=manual`) |
| Add members | `POST /groups/{id}/members` `{"page_ids":["p_2"]}` | `200 Group` |
| Remove member | `DELETE /groups/{id}/members/{page_id}` | `200 Group` |
| Accept suggested group | `POST /groups/{id}/accept` | `200 Group` |
| Delete | `DELETE /groups/{id}` | `204` (pages remain) |

## 7. Notes & highlights
| Feature | Request | Response |
|---|---|---|
| List for target | `GET /workspaces/{id}/notes?target_type=page&target_id=p_1` | `200 {items:[Note]}` |
| Create | `POST /workspaces/{id}/notes` `{"target_type":"page","target_id":"p_1","kind":"note","body":"...","quote":null,"author":"Asha"}` | `201 Note` |
| Update | `PATCH /notes/{id}` `{"body":"..."}` | `200 Note` |
| Delete | `DELETE /notes/{id}` | `204` |

## 8. Tags
| Feature | Request | Response |
|---|---|---|
| List | `GET /workspaces/{id}/tags` | `200 {items:[{"id","name","color","count"}]}` |
| Create | `POST /workspaces/{id}/tags` `{"name":"key","color":"#f59e0b"}` | `201 Tag`; `409` if name exists |
| Update / delete | `PATCH /tags/{id}` · `DELETE /tags/{id}` | `200 Tag` · `204` |
| Attach | `POST /tags/{id}/attach` `{"target_type":"page","target_id":"p_1"}` | `204` |
| Detach | `POST /tags/{id}/detach` same body | `204` |

## 9. Search
| Feature | Request | Response |
|---|---|---|
| Search | `GET /workspaces/{id}/search?q=triage&scope=all&limit=20` (supports `#tag`, `@domain` tokens in `q`) | `200 {"query":"triage","results":[{"type":"page|note|tag|group","id":"...","page_id":"p_1","title":"...","snippet":"...<mark>triage</mark>...","score":0.91}]}` |

## 10. Processing
| Feature | Request | Response |
|---|---|---|
| Recompute relationships | `POST /workspaces/{id}/process` `{"edge_threshold":0.35,"louvain_resolution":1.0}` (body optional) | `202 {"job_id":"j_1"}` |
| Job status | `GET /jobs/{id}` | `200 {"id","kind","state":"queued|running|done|failed","error":null}` |
| Workspace processing summary | `GET /workspaces/{id}/processing` | `200 {"queued":2,"running":1,"failed":0,"ready":14,"last_recompute_at":"..."}` |

## 11. Export / Import
| Feature | Request | Response |
|---|---|---|
| Export JSON | `GET /workspaces/{id}/export?format=json&include_text=false` | `200` `Content-Disposition: attachment; filename="<name>.mindloom.json"` body below |
| Export Markdown | `GET /workspaces/{id}/export?format=md` | `200 text/markdown` |
| Import JSON | `POST /workspaces/import` (`multipart/form-data` file, or JSON body) | `201 Workspace` (new workspace, new ids) |

```json
{"schema_version":1,"exported_at":"...","workspace":{"name":"...","settings":{},"view_state":{}},
 "pages":[{"id","url","canonical_url","title","domain","summary","keywords","pos","importance","tags":["key"]}],
 "groups":[{"id","name","category","color","origin","page_ids":[]}],
 "edges":[{"source","target","type","label","origin","status","confidence","evidence"}],
 "notes":[{"target_type","target_id","kind","body","quote"}]}
```

## 12. Sharing
| Feature | Request | Response |
|---|---|---|
| Create link | `POST /workspaces/{id}/share` `{"role":"view","expires_in_days":7}` | `201 {"id","token","role","url":"http://localhost:5173/s/<token>","expires_at"}` |
| List links | `GET /workspaces/{id}/shares` | `200 {items:[ShareLink]}` |
| Revoke | `DELETE /shares/{id}` | `204` |
| Resolve token | `GET /shared/{token}` | `200 {"workspace_id","role"}`; then normal endpoints with `X-Share-Token` |

Role rules: `view` → GET only (write calls return `403 forbidden`); `edit` → notes, tags, edges, groups, positions; not workspace delete or share management.

## 13. WebSocket
`GET ws://localhost:8000/ws/workspaces/{id}?share=<token optional>`

Owner-session connections work without `share`. A valid, unexpired workspace share token (`view` or `edit`) also permits a connection; invalid, revoked, expired, or cross-workspace tokens close with code `4403`.

Envelope: `{"type":"page.processing_completed","workspace_id":"w_1","seq":43,"ts":"...","data":{...}}`

| type | data |
|---|---|
| `hello` | `{"seq":42}` (sent on connect) |
| `page.discovered` | `{"page":Page}` |
| `page.extraction_completed` | `{"page_id","status":"extracted"}` |
| `page.extraction_failed` | `{"page_id","error_code","error_message"}` |
| `page.processing_completed` | `{"page":Page}` (with summary/keywords) |
| `page.processing_failed` | `{"page_id","error_message"}` |
| `graph.changed` | `{"changed":{"pages":["p_1"],"edges":["e_1"],"groups":["g_1"]},"reason":"recompute|manual_edit"}` |
| `workspace.updated` | `{"workspace":Workspace}` |
| `ping` | `{}` every 25 s; client replies `{"type":"pong"}` |

Client rules: if `seq` jumps by >1 or socket reconnects, call `GET /workspaces/{id}/graph` and reset the local store. Reconnect backoff 1→30 s.

## 14. Extension ↔ Dashboard bridge (not HTTP — reference)
Messages via `window.postMessage({source:"mindloom", id, type, payload}, origin)`; see `spec.md` §M2 for the full list (`PING/PONG`, `START`, `STOP`, `COLLECT_NOW`, `LIST_TABS`, `GET_STATUS`, `STATUS`, `TABS`, `TAB_RESULT`).

## 15. Example: full ingest cURL
```bash
curl -X POST http://localhost:8000/api/v1/workspaces/w_1/pages \
  -H 'Content-Type: application/json' \
  -d '{"client_event_id":"8b1e...","url":"https://example.com/a?utm_source=x","title":"A","text":"Hello research world...","meta":{},"extraction":{"status":"ok","method":"readability"},"tab":{"browser_tab_id":12,"active":false},"captured_at":"2026-10-01T10:00:00Z"}'
```
