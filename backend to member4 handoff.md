Mindloom: ML & Intelligence Integration Handoff (Member 4)

Current System State

The core backend infrastructure (Milestone 1 & 2) is fully implemented and verified. The FastAPI server handles idempotency, real-time WebSocket broadcasting, and PostgreSQL/pgvector persistence. The background asyncio job queue is actively running and managing page analysis lifecycles.

Currently, the NLP pipeline is bypassed using hardcoded stubs. Your objective is to replace these stubs with actual Machine Learning logic.

Your Working Directory

Your primary work will be contained entirely within:

backend/app/intelligence/interface.py

You will not need to build the API endpoints, database queries, or the WebSocket emitters—the job queue already handles the data flow and will automatically pass the necessary inputs into your interface functions.

Primary Objectives

1\. NLP Pipeline & Embeddings (process\_page)

The queue passes extracted text to process\_page(text: str). You must implement:

Summarization: Extract a concise 2-3 sentence summary using a lightweight technique (e.g., TF-IDF scoring or a small transformer).

Entity/Keyword Extraction: Extract the top 5-10 core concepts from the text.

Vector Embeddings: Generate a 384-dimensional semantic embedding for the page text using a model like all-MiniLM-L6-v2 via sentence-transformers and PyTorch.

Output: Return a dictionary matching the PageAnalysisCreate schema.

2\. Graph Edge Generation (compute\_relationships)

The queue calls compute\_relationships(workspace\_id, new\_page\_id) after a page is analyzed. You must implement:

Similarity Scoring: Compare the new page's embedding against existing pages in the workspace (the backend will provide the fetch method).

Edge Suggestions: Generate connections for pairs with high cosine similarity (e.g., > 0.75).

Community Detection (Optional but recommended): Apply NetworkX and a clustering algorithm (like Louvain) to group heavily related nodes.

Output: Return a list of EdgeCreate dictionaries with origin="suggested" and calculated confidence scores.

Architectural Constraints & Guardrails

Non-Blocking Execution: The background job queue runs in an asynchronous event loop. Because PyTorch and Scikit-learn operations are CPU-bound and blocking, you must wrap your heavy ML executions in asyncio.to\_thread() within the interface methods.

Cold Starts & Memory: Load your ML models (e.g., SentenceTransformer) into memory once at the module level or application startup, not dynamically inside the function call, to prevent memory leaks and severe performance degradation on each job.

Dependencies: Add your required ML libraries (torch, sentence-transformers, scikit-learn, networkx, spacy, etc.) to the backend requirements.txt or pyproject.toml. Keep the models as lightweight as possible to ensure local execution remains feasible.

Required Documentation References

Before writing the implementation, review the strict data structures and system expectations outlined in the repository documentation:

docs/spec.md (Phase 5 & 8): Details the exact lifecycle of the AI processing and the expectation for edge generation.

docs/api.md (Sections 5, 9, 13): Review the PageAnalysisCreate and EdgeCreate schemas to ensure your functions return the exact dictionaries the backend expects.

docs/Data-model.md (Table: page\_analysis & edges): Outlines the pgvector column constraints (specifically the 384-dimension limit) and the override behavior for suggested edges.

docs/task.md (Member 4 section): Outlines your specific grading criteria and project responsibilities for the semantic search and intelligence layer.