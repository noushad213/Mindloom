# Member 4 — Research Intelligence & Pipeline Architecture

This document provides a comprehensive overview of **Member 4's Research Intelligence and NLP Pipeline** in Mindloom.

---

## 1. Overview & Architecture

Member 4 owns the **NLP, Machine Learning, Relationship Mining, and Quality Verification** domain.

When pages are ingested via the browser extension (Member 2) and stored in PostgreSQL (Member 3), the backend background job runner ([queue.py](file:///c:/Users/Lenovo/Desktop/mindloom_av/Mindloom/backend/app/jobs/queue.py)) asynchronously calls Member 4's processing functions inside:

📁 `backend/app/intelligence/interface.py`

```
┌───────────────────────────────┐
│ Browser Extension / Ingest API│
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ FastAPI Job Queue (queue.py)  │
└───────────────┬───────────────┘
                │ asyncio.to_thread()
                ▼
┌────────────────────────────────────────────────────────┐
│ Member 4 Pure Intelligence Boundary (interface.py)     │
├────────────────────────────────────────────────────────┤
│ 1. clean_main_content()      -> Strips HTML/Scripts    │
│ 2. extract_keywords()        -> TF-IDF Term Weighting  │
│ 3. generate_extractive_sum() -> Keyword Density Sum.   │
│ 4. compute_simhash()         -> 64-bit SimHash Hex     │
│ 5. generate_embedding()      -> 384-d MiniLM Vector    │
│ 6. compute_relationships()   -> Cosine Sim + Evidence  │
│ 7. Dynamic Topic Clustering  -> Keyword Connected Groups│
└────────────────────────────────────────────────────────┘
```

---

## 2. Interface Contract

The intelligence interface exposes three core functions:

### A. `process_page(text: str, title: str, url: str) -> PageAnalysisResult`
Processes an individual page's raw text and returns:
- **`cleaned_text`**: Stripped of HTML tags, script residue, boilerplate headers/footers, and duplicate spaces.
- **`summary`**: 2–3 sentence extractive summary based on keyword density.
- **`keywords`**: Top 8 salient terms extracted using term-frequency heuristics excluding stop-words.
- **`simhash`**: 16-character hexadecimal 64-bit SimHash for near-duplicate identification.
- **`embedding`**: 384-dimensional vector list generated via `SentenceTransformer("all-MiniLM-L6-v2")` (with deterministic normalized TF-IDF hash projection fallback if `sentence-transformers` is absent).
- **`summary_method`**: `"extractive"`
- **`embedding_model`**: `"all-MiniLM-L6-v2"` or `"tfidf-hash-384"`

### B. `compute_relationships(pages: list[Any], rejected_pairs: set[tuple[str, str]], params: Any) -> RelationshipResult`
Generates suggested graph connections and topic clusters across all pages in a workspace:
- **Similarity Threshold**: Default `0.35` (configurable via `params["edge_threshold"]`).
- **Edge Type**:
  - `"duplicate_of"`: If Cosine Similarity $\ge 0.95$ or SimHash fingerprint matches.
  - `"related_to"`: If Cosine Similarity reaches `edge_threshold`.
- **Explainable Evidence**: Every suggested edge includes a JSON object with `method`, `score`, `shared_keywords`, and `snippets`.
- **Stored Features**: Recompute uses saved page embeddings, keywords, and SimHash values from `page_analysis`.
- **Manual Overrides**: Any pair present in `rejected_pairs` is strictly skipped and will never be re-suggested.
- **Topic Clusters**: Groups connected nodes into named topic clusters with assigned color palettes (e.g. `"Topic: Fastapi"`).

### C. `embed_query(query: str) -> list[float] | None`
Generates a 384-dimensional query vector for search & semantic indexing.

---

## 3. Fallback & Execution Guardrails

1. **Lazy Model Singleton**: `SentenceTransformer("all-MiniLM-L6-v2")` is loaded lazily once per process under a thread lock.
2. **Logged Fallback**: Model loading and inference failures are logged before the module switches to a 384-dimensional lexical hash vector.
3. **Non-blocking Execution**: All CPU-heavy processing is called via `asyncio.to_thread` from [queue.py](file:///c:/Users/Lenovo/Desktop/mindloom_av/Mindloom/backend/app/jobs/queue.py).

---

## 4. Testing & Verification

Unit tests for the intelligence pipeline are located at:

📁 `backend/tests/unit/test_intelligence.py`

Run tests using pytest:
```bash
python -m pytest backend/tests/unit/test_intelligence.py
```

---

## 5. Handoff Notes for Teammates & AI Agents

* **Member 3 (Backend):** Call `process_page` during single page ingest jobs, and `compute_relationships` during workspace recompute jobs. Do not alter the return types `PageAnalysisResult` and `RelationshipResult`.
* **Member 1 (Noushad - Frontend):** Edge objects contain an `evidence` string and a `confidence` float. Display these in the edge detail modal / popover.
* **Member 2 (Extension):** Ensure the `text` field in page payloads contains full page `innerText` or Readability output for optimal keyword extraction and summarization.
