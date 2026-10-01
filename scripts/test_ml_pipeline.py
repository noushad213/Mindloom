"""Exercise Mindloom intelligence functions without an API or database.

Run from the repository root with ``python scripts/test_ml_pipeline.py``.
The script runs every check, prints a pass/fail summary, and exits nonzero if
an assertion fails. The first page call measures model cold start; the next
call measures warm inference in the same process.
"""

from __future__ import annotations

import math
import re
import sys
import time
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.intelligence import interface as ml  # noqa: E402


SAMPLE_TEXT = (
    "FastAPI handles HTTP requests through Python ASGI routes. "
    "Uvicorn serves those applications with an asynchronous event loop. "
    "Mindloom stores research pages and exposes their relationships as a graph. "
    "Search combines article text with vector similarity to find related work."
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def valid_vector(vector: object) -> bool:
    return (isinstance(vector, list) and len(vector) == 384 and
            all(isinstance(value, float) and math.isfinite(value) for value in vector))


def analyze(text: str, title: str) -> ml.PageAnalysisResult:
    # This is the actual worker boundary: process_page(text, title, url).
    return ml.process_page(text=text, title=title, url="https://example.com/research")


def main() -> int:
    outcomes: list[tuple[str, bool, str]] = []

    def run_check(name: str, check) -> None:
        try:
            detail = check() or "ok"
            outcomes.append((name, True, str(detail)))
            print(f"PASS {name}: {detail}", flush=True)
        except Exception as exc:
            outcomes.append((name, False, f"{type(exc).__name__}: {exc}"))
            print(f"FAIL {name}: {type(exc).__name__}: {exc}", flush=True)

    print("Mindloom ML pipeline: isolated validation", flush=True)
    started = time.perf_counter()
    try:
        sample = analyze(SAMPLE_TEXT, "FastAPI research workspace")
        cold_seconds = time.perf_counter() - started
        print(f"MODEL first call: {sample.embedding_model}; cold-start: {cold_seconds:.3f}s", flush=True)
    except Exception as exc:
        sample = None
        cold_seconds = time.perf_counter() - started
        print(f"MODEL first call failed after {cold_seconds:.3f}s: {type(exc).__name__}: {exc}", flush=True)

    def vector_check() -> str:
        require(sample is not None, "process_page raised before returning")
        require(valid_vector(sample.embedding), "page embedding must contain exactly 384 finite Python floats")
        query = ml.embed_query("FastAPI web routing")
        require(valid_vector(query), "embed_query must contain exactly 384 finite Python floats")
        return f"page and query vectors have 384 finite floats; model={sample.embedding_model}"

    run_check("1. vector dimension and type", vector_check)

    def summary_check() -> str:
        require(sample is not None, "process_page raised before returning")
        require(isinstance(sample.summary, str) and bool(sample.summary.strip()), "summary is empty")
        require(len(sample.summary) <= 400, "summary exceeds the 400-character data contract")
        sentences = re.findall(r"[^.!?]+[.!?]", sample.summary)
        require(2 <= len(sentences) <= 3, "sample summary must contain 2–3 sentences")
        require(isinstance(sample.keywords, list) and bool(sample.keywords), "keywords list is empty")
        require(all(isinstance(word, str) and word.strip() for word in sample.keywords),
                "keywords must be nonempty strings")
        return f"{len(sentences)} sentences, {len(sample.keywords)} keywords, {len(sample.summary)} characters"

    run_check("2. summary and keywords", summary_check)

    def semantic_check() -> str:
        anchor = analyze("FastAPI async routing", "FastAPI routing")
        related = analyze("Uvicorn ASGI server", "ASGI server")
        unrelated = analyze("Chocolate cake recipe", "Baking")
        require(all(valid_vector(item.embedding) for item in (anchor, related, unrelated)),
                "one semantic test vector is invalid")
        related_score = ml.cosine_similarity(anchor.embedding, related.embedding)
        unrelated_score = ml.cosine_similarity(anchor.embedding, unrelated.embedding)
        print(f"SEMANTIC cosine related={related_score:.3f}, unrelated={unrelated_score:.3f}", flush=True)
        require(related_score > unrelated_score + 0.15,
                "related snippets must exceed unrelated snippets by at least 0.15 cosine")
        return f"related={related_score:.3f}, unrelated={unrelated_score:.3f}"

    run_check("3. semantic cosine separation", semantic_check)

    def benchmark_check() -> str:
        require(sample is not None, "cold-start call failed")
        warm_started = time.perf_counter()
        warm = analyze(SAMPLE_TEXT, "FastAPI research workspace")
        warm_seconds = time.perf_counter() - warm_started
        require(valid_vector(warm.embedding), "warm-call vector is invalid")
        return f"cold-start={cold_seconds:.3f}s, warm-start={warm_seconds:.3f}s; model={warm.embedding_model}"

    run_check("4. cold and warm latency", benchmark_check)

    def relationship_contract_check() -> str:
        first_id, second_id = str(uuid4()), str(uuid4())
        repeated = "Python FastAPI routing and ASGI server research. " * 3
        pages = [{"id": first_id, "title": "Research A", "url": "https://example.com/a", "text": repeated},
                 {"id": second_id, "title": "Research B", "url": "https://example.com/b", "text": repeated}]
        relationships = ml.compute_relationships(pages, set(), {"edge_threshold": 0.35})
        require(relationships.candidate_edges, "identical research pages produced no candidate edge")
        violations: list[str] = []
        for edge in relationships.candidate_edges:
            if edge.get("source") not in {first_id, second_id} or edge.get("target") not in {first_id, second_id}:
                violations.append("source/target IDs are invalid")
            if edge.get("origin") != "suggested":
                violations.append("origin=suggested is missing")
            confidence = edge.get("confidence")
            if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
                violations.append("confidence is outside [0, 1]")
            evidence = edge.get("evidence")
            if not isinstance(evidence, dict) or not {"method", "score", "shared_keywords", "snippets"} <= set(evidence):
                violations.append("evidence is not the documented JSON object")
        require(not violations, "; ".join(sorted(set(violations))))
        return f"{len(relationships.candidate_edges)} candidate edge(s) match persistence contracts"

    run_check("5. suggested-edge data contract", relationship_contract_check)

    def input_fallback_check() -> str:
        empty = analyze("", "",)
        require(isinstance(empty.summary, str) and bool(empty.summary.strip()), "empty input has no safe summary")
        short = analyze("AI helps.", "Short snippet")
        require(isinstance(short.summary, str) and bool(short.summary.strip()), "short snippet has no summary")
        non_english = analyze("人工智能正在帮助医生分析研究资料。", "中文研究")
        require(valid_vector(non_english.embedding), "non-English input has an invalid vector")
        require(any(value != 0.0 for value in non_english.embedding),
                "non-English input produced a zero vector")
        return "empty, short, and non-English inputs have safe output"

    run_check("6. empty, short, and non-English inputs", input_fallback_check)

    def size_limit_check() -> str:
        long_text = "research " * 12_501  # >100,000 characters after whitespace collapse.
        cleaned = ml.clean_main_content(long_text)
        require(len(cleaned) <= 50_000, "cleaned text exceeds the 50,000-character processing limit")
        return f"cleaned oversized input to {len(cleaned)} characters"

    run_check("7. oversized input limit", size_limit_check)

    def summary_limit_check() -> str:
        long_sentence = "Research data provides important clinical context and detailed evidence " * 4
        text = ". ".join((long_sentence, long_sentence, long_sentence)) + "."
        summary = ml.generate_extractive_summary(text, "Long research page")
        require(len(summary) <= 400, f"generated summary is {len(summary)} characters; maximum is 400")
        return f"summary length={len(summary)} characters"

    run_check("8. summary length limit", summary_limit_check)

    def fallback_check() -> str:
        saved_model, saved_loaded = ml._MODEL_SINGLETON, ml._MODEL_LOADED
        try:
            ml._MODEL_SINGLETON = None
            ml._MODEL_LOADED = True
            anchor, model_name = ml.generate_embedding("FastAPI async routing")
            related, _ = ml.generate_embedding("Uvicorn ASGI server")
            non_english, _ = ml.generate_embedding("人工智能帮助医生")
            require(model_name == "tfidf-hash-384", "fallback did not identify itself")
            require(all(valid_vector(vector) for vector in (anchor, related, non_english)),
                    "fallback returned an invalid vector")
            related_score = ml.cosine_similarity(anchor, related)
            non_english_norm = math.sqrt(sum(value * value for value in non_english))
            print(f"FALLBACK related cosine={related_score:.3f}, non-English norm={non_english_norm:.3f}", flush=True)
            return "deterministic fallback is shape-safe; semantic quality is reported above"
        finally:
            ml._MODEL_SINGLETON, ml._MODEL_LOADED = saved_model, saved_loaded

    run_check("9. deterministic fallback behavior", fallback_check)

    failures = [name for name, passed, _ in outcomes if not passed]
    print(f"RESULT {len(outcomes) - len(failures)}/{len(outcomes)} checks passed", flush=True)
    if failures:
        print("FAILED CHECKS: " + ", ".join(failures), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
