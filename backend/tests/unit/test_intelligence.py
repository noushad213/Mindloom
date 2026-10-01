"""Unit tests for Member 4's intelligence pipeline in app.intelligence.interface."""

import pytest
from app.intelligence import interface as intelligence
from app.intelligence.interface import (
    process_page,
    compute_relationships,
    clean_main_content,
    extract_keywords,
    generate_extractive_summary,
    compute_simhash,
    cosine_similarity,
    embed_query,
    EMBEDDING_DIM
)


def test_clean_main_content():
    html_text = "<p>Hello <b>world</b>!</p><script>alert('test')</script> Visit https://example.com"
    cleaned = clean_main_content(html_text)
    assert "Hello world" in cleaned
    assert "<p>" not in cleaned
    assert "https://" not in cleaned


def test_extract_keywords():
    text = "FastAPI is a modern web framework for Python. FastAPI is fast and easy to build APIs."
    keywords = extract_keywords(text, top_n=5)
    assert "fastapi" in keywords
    assert "framework" in keywords or "python" in keywords


def test_generate_extractive_summary():
    text = "Browser extensions enhance web functionality. Mindloom is a research workspace manager. It collects tabs and generates knowledge graphs."
    summary = generate_extractive_summary(text, title="Mindloom Overview", num_sentences=2)
    assert len(summary) > 0
    assert summary != "Mindloom Overview"


def test_compute_simhash():
    text1 = "This is a web page about Python browser extensions."
    text2 = "This is a web page about Python browser extensions."
    text3 = "Unrelated article about deep sea fishing techniques."
    
    hash1 = compute_simhash(text1)
    hash2 = compute_simhash(text2)
    hash3 = compute_simhash(text3)

    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 16


def test_process_page():
    text = "Machine learning and artificial intelligence are revolutionizing web search and visual graph research tools."
    result = process_page(text=text, title="AI Web Search", url="https://example.com/ai")

    assert result.cleaned_text != ""
    assert result.summary != ""
    assert len(result.keywords) > 0
    assert result.simhash is not None
    assert result.embedding is not None
    assert len(result.embedding) == EMBEDDING_DIM
    assert result.summary_method == "extractive"


def test_compute_relationships():
    pages = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "title": "FastAPI Web Framework",
            "url": "https://fastapi.tiangolo.com",
            "text": "FastAPI is a high performance web framework for building APIs with Python."
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "title": "Python API Development",
            "url": "https://python.org/apis",
            "text": "Building high performance APIs with Python using modern async web frameworks like FastAPI."
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "title": "Cooking Spaghetti Carbonara",
            "url": "https://recipes.com/spaghetti",
            "text": "Spaghetti carbonara requires eggs, guanciale, pecorino cheese, and black pepper."
        }
    ]

    rejected_pairs = set()
    result = compute_relationships(pages, rejected_pairs, params={"edge_threshold": 0.5})

    assert len(result.candidate_edges) >= 1
    edge = result.candidate_edges[0]
    assert edge["source"] in ["11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"]
    assert edge["target"] in ["11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"]
    assert "evidence" in edge
    assert "confidence" in edge
    assert edge["origin"] == "suggested"
    assert isinstance(edge["evidence"], dict)


def test_compute_relationships_respects_rejected_pairs():
    id1 = "11111111-1111-1111-1111-111111111111"
    id2 = "22222222-2222-2222-2222-222222222222"
    pages = [
        {"id": id1, "title": "Page A", "url": "https://a.com", "text": "Python FastAPI performance test."},
        {"id": id2, "title": "Page B", "url": "https://b.com", "text": "Python FastAPI performance test."}
    ]

    rejected_pairs = {(id1, id2)}
    result = compute_relationships(pages, rejected_pairs, params={"edge_threshold": 0.1})

    assert len(result.candidate_edges) == 0


def test_embed_query():
    query_vec = embed_query("Python web framework")
    assert query_vec is not None
    assert len(query_vec) == EMBEDDING_DIM


def test_process_page_caps_model_inputs_and_summary(monkeypatch):
    observed = {}

    def summarize(text, title):
        observed["summary_input"] = len(text)
        return "a" * 500

    def embed(text):
        observed["embedding_input"] = len(text)
        return [0.0] * EMBEDDING_DIM, "test-model"

    monkeypatch.setattr(intelligence, "generate_extractive_summary", summarize)
    monkeypatch.setattr(intelligence, "generate_embedding", embed)
    result = process_page("x" * 100_001, "Oversized", "https://example.com")

    assert observed == {"summary_input": 50_000, "embedding_input": 50_000}
    assert result.summary == "a" * 397 + "..."


def test_compute_relationships_uses_stored_embeddings(monkeypatch):
    def reject_inference(_text):
        raise AssertionError("recompute must not embed analyzed pages again")

    monkeypatch.setattr(intelligence, "generate_embedding", reject_inference)
    embedding = [0.0] * EMBEDDING_DIM
    embedding[0] = 1.0
    pages = [
        {"id": "11111111-1111-1111-1111-111111111111", "title": "A", "text": "same topic",
         "embedding": embedding, "keywords": ["topic"], "simhash": "0" * 16},
        {"id": "22222222-2222-2222-2222-222222222222", "title": "B", "text": "same topic",
         "embedding": embedding, "keywords": ["topic"], "simhash": "0" * 16},
    ]

    result = compute_relationships(pages, set(), {"edge_threshold": 0.9})

    assert len(result.candidate_edges) == 1
    assert isinstance(result.candidate_edges[0]["evidence"], dict)
