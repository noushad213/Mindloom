"""Member 4's Intelligence and Research Pipeline.

Provides content cleaning, keyword extraction, extractive summarization,
SimHash duplicate detection, 384-dimensional semantic embeddings (SentenceTransformers
with TF-IDF/hash fallback), explainable relationship scoring, and topic clustering.
"""

from dataclasses import dataclass
import hashlib
import logging
import math
import re
import threading
from typing import Any, List, Dict, Set, Tuple

# Lazy-loaded model singleton to prevent cold start penalties and memory overhead
_MODEL_SINGLETON: Any = None
_MODEL_LOADED: bool = False
_MODEL_LOCK = threading.Lock()
logger = logging.getLogger(__name__)
EMBEDDING_DIM = 384
MAX_INPUT_CHARS = 50_000
MAX_SUMMARY_CHARS = 400

# Default English stopwords list for light NLP fallback
ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing",
    "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves", "http", "https", "com", "org", "net", "page", "site", "web"
}


@dataclass(frozen=True)
class PageAnalysisResult:
    cleaned_text: str
    summary: str
    keywords: list[str]
    simhash: str | None
    embedding: list[float] | None
    summary_method: str | None = None
    embedding_model: str | None = None


@dataclass(frozen=True)
class RelationshipResult:
    candidate_edges: list[dict[str, Any]]
    clusters: list[dict[str, Any]]


def _get_sentence_transformer() -> Tuple[Any, str]:
    """Load the model once per process; report failures before using the fallback."""
    global _MODEL_SINGLETON, _MODEL_LOADED
    if not _MODEL_LOADED:
        with _MODEL_LOCK:
            if not _MODEL_LOADED:
                try:
                    from sentence_transformers import SentenceTransformer
                    _MODEL_SINGLETON = SentenceTransformer("all-MiniLM-L6-v2")
                except Exception:
                    logger.exception("Could not load all-MiniLM-L6-v2; using the lexical hash fallback")
                    _MODEL_SINGLETON = None
                finally:
                    _MODEL_LOADED = True
    return _MODEL_SINGLETON, ("all-MiniLM-L6-v2" if _MODEL_SINGLETON is not None else "tfidf-hash-384")


def clean_main_content(text: str) -> str:
    """Strips HTML tags, scripts, header/footer noise, and normalizes whitespace."""
    if not text:
        return ""
    text = text[:MAX_INPUT_CHARS]
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Strip URLs
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:MAX_INPUT_CHARS]


def _limit_summary(summary: str) -> str:
    return summary if len(summary) <= MAX_SUMMARY_CHARS else summary[:MAX_SUMMARY_CHARS - 3] + "..."


def extract_keywords(text: str, top_n: int = 8) -> List[str]:
    """Extracts top N significant keywords based on term frequency excluding stopwords."""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    filtered_words = [w for w in words if w not in ENGLISH_STOPWORDS]
    if not filtered_words:
        return []
    
    counts: Dict[str, int] = {}
    for word in filtered_words:
        counts[word] = counts.get(word, 0) + 1
        
    sorted_keywords = sorted(counts.keys(), key=lambda w: counts[w], reverse=True)
    return sorted_keywords[:top_n]


def generate_extractive_summary(text: str, title: str, num_sentences: int = 3) -> str:
    """Generates a concise extractive summary based on keyword density."""
    if not text:
        return _limit_summary(title or "Untitled Page")

    sentences = re.split(r"(?<=[.!?]) +", text)
    if len(sentences) <= num_sentences:
        return _limit_summary(" ".join(sentences))

    keywords = set(extract_keywords(text, top_n=15))
    sentence_scores: List[Tuple[float, int, str]] = []

    for idx, sentence in enumerate(sentences):
        words = re.findall(r"\b[a-zA-Z]{3,}\b", sentence.lower())
        if not words:
            continue
        score = sum(1 for w in words if w in keywords) / len(words)
        # Give slight boost to earlier sentences
        score += (1.0 / (idx + 1)) * 0.2
        sentence_scores.append((score, idx, sentence))

    sentence_scores.sort(key=lambda x: x[0], reverse=True)
    top_sentences = sorted(sentence_scores[:num_sentences], key=lambda x: x[1])
    
    summary = " ".join([s[2] for s in top_sentences])
    return _limit_summary(summary if summary else title)


def compute_simhash(text: str) -> str:
    """Computes a 64-bit SimHash hex string for content deduplication."""
    tokens = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
    if not tokens:
        return "0" * 16

    v = [0] * 64
    for token in tokens:
        token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        for i in range(64):
            bit = (token_hash >> i) & 1
            v[i] += 1 if bit == 1 else -1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)

    return f"{fingerprint:016x}"


def generate_embedding(text: str) -> Tuple[List[float], str]:
    """Generates a 384-dimensional vector embedding.
    
    Uses SentenceTransformer if available, otherwise falls back to a deterministic 384-dim TF-IDF hash projection.
    """
    model, model_name = _get_sentence_transformer()
    if model is not None:
        try:
            vec = [float(value) for value in model.encode(text, convert_to_numpy=True).tolist()]
            if len(vec) != EMBEDDING_DIM or not all(math.isfinite(value) for value in vec):
                raise ValueError("SentenceTransformer returned an invalid embedding")
            return vec, model_name
        except Exception:
            logger.exception("SentenceTransformer inference failed; using the lexical hash fallback")

    # Fallback: Deterministic 384-dimensional normalized word feature vector
    vector = [0.0] * EMBEDDING_DIM
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    for word in words:
        if word in ENGLISH_STOPWORDS:
            continue
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        index = h % EMBEDDING_DIM
        weight = 1.0 + (h % 10) / 10.0
        vector[index] += weight

    norm = math.sqrt(sum(val * val for val in vector))
    if norm > 0:
        vector = [val / norm for val in vector]
    
    return vector, "tfidf-hash-384"


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Computes cosine similarity between two vector lists."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def process_page(text: str, title: str, url: str) -> PageAnalysisResult:
    """Processes page content: cleans text, generates summary, extracts keywords,
    calculates SimHash, and generates a 384-d semantic embedding."""
    cleaned = clean_main_content((text or "")[:MAX_INPUT_CHARS])
    if not cleaned:
        cleaned = (title or url)[:MAX_INPUT_CHARS]
        
    summary = _limit_summary(generate_extractive_summary(cleaned, title=title))
    keywords = extract_keywords(cleaned, top_n=8)
    simhash_str = compute_simhash(cleaned)
    embedding, model_name = generate_embedding(cleaned)

    return PageAnalysisResult(
        cleaned_text=cleaned,
        summary=summary,
        keywords=keywords,
        simhash=simhash_str,
        embedding=embedding,
        summary_method="extractive",
        embedding_model=model_name,
    )


def compute_relationships(pages: list[Any], rejected_pairs: set[tuple[str, str]], params: Any) -> RelationshipResult:
    """Computes candidate edges and topic clusters across workspace pages.
    
    Respects manual overrides in rejected_pairs.
    """
    if not pages or len(pages) < 2:
        return RelationshipResult(candidate_edges=[], clusters=[])

    threshold = 0.35
    if isinstance(params, dict):
        threshold = float(params.get("edge_threshold", threshold))

    processed_pages: List[Dict[str, Any]] = []
    for p in pages:
        p_id = str(p.get("id") if isinstance(p, dict) else getattr(p, "id"))
        p_title = str((p.get("title") if isinstance(p, dict) else getattr(p, "title", "")) or "")
        p_text = clean_main_content(str((p.get("text") if isinstance(p, dict) else getattr(p, "text", "")) or ""))
        cached_keywords = p.get("keywords") if isinstance(p, dict) else getattr(p, "keywords", None)
        cached_simhash = p.get("simhash") if isinstance(p, dict) else getattr(p, "simhash", None)
        cached_embedding = p.get("embedding") if isinstance(p, dict) else getattr(p, "embedding", None)

        keywords = list(cached_keywords) if cached_keywords is not None else extract_keywords(p_text, top_n=8)
        simhash_str = cached_simhash if cached_simhash is not None else compute_simhash(p_text)
        if cached_embedding is not None:
            embedding = [float(value) for value in cached_embedding]
            if len(embedding) != EMBEDDING_DIM or not all(math.isfinite(value) for value in embedding):
                raise ValueError(f"Page {p_id} has an invalid stored embedding")
        else:
            embedding, _ = generate_embedding(p_text)

        processed_pages.append({
            "id": p_id,
            "title": p_title,
            "text": p_text,
            "keywords": keywords,
            "simhash": simhash_str,
            "embedding": embedding
        })

    candidate_edges: List[Dict[str, Any]] = []
    connected_adj: Dict[str, Set[str]] = {p["id"]: set() for p in processed_pages}

    for i in range(len(processed_pages)):
        for j in range(i + 1, len(processed_pages)):
            p1 = processed_pages[i]
            p2 = processed_pages[j]
            id1, id2 = p1["id"], p2["id"]

            # Skip rejected pairs (manual overrides)
            if (id1, id2) in rejected_pairs or (id2, id1) in rejected_pairs:
                continue

            sim_score = cosine_similarity(p1["embedding"], p2["embedding"])
            is_dup = (p1["simhash"] == p2["simhash"] and p1["simhash"] != "0" * 16) or sim_score >= 0.95

            if is_dup or sim_score >= threshold:
                shared_kw = sorted(set(p1["keywords"]).intersection(set(p2["keywords"])))

                edge_type = "duplicate_of" if is_dup else "related_to"
                label = "Duplicate Content" if is_dup else f"Related ({int(sim_score * 100)}%)"
                bounded_score = min(1.0, max(0.0, sim_score))
                evidence = {
                    "method": "simhash+cosine" if is_dup else "embedding_cosine+keywords",
                    "score": round(bounded_score, 4),
                    "similarity": round(sim_score, 4),
                    "shared_keywords": shared_kw,
                    "snippets": [
                        {"page_id": id1, "text": p1["text"][:200]},
                        {"page_id": id2, "text": p2["text"][:200]},
                    ],
                }

                candidate_edges.append({
                    "source": id1,
                    "target": id2,
                    "type": edge_type,
                    "label": label,
                    "origin": "suggested",
                    "status": "suggested",
                    "confidence": round(bounded_score, 2),
                    "evidence": evidence
                })
                connected_adj[id1].add(id2)
                connected_adj[id2].add(id1)

    # Simple connected components for topic clustering
    visited: Set[str] = set()
    clusters: List[Dict[str, Any]] = []
    color_palette = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4"]
    cluster_idx = 0

    for p in processed_pages:
        p_id = p["id"]
        if p_id in visited or not connected_adj[p_id]:
            continue

        component: List[str] = []
        queue = [p_id]
        visited.add(p_id)

        while queue:
            curr = queue.pop(0)
            component.append(curr)
            for neighbor in connected_adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if len(component) >= 2:
            # Gather common keywords for cluster naming
            cluster_kws: Dict[str, int] = {}
            for comp_id in component:
                comp_p = next((page for page in processed_pages if page["id"] == comp_id), None)
                if comp_p:
                    for kw in comp_p["keywords"]:
                        cluster_kws[kw] = cluster_kws.get(kw, 0) + 1

            sorted_kws = sorted(cluster_kws.keys(), key=lambda k: cluster_kws[k], reverse=True)
            topic_name = f"Topic: {sorted_kws[0].capitalize()}" if sorted_kws else f"Topic Cluster {cluster_idx + 1}"
            color = color_palette[cluster_idx % len(color_palette)]

            clusters.append({
                "name": topic_name,
                "category": "topic",
                "color": color,
                "keywords": sorted_kws[:5],
                "page_ids": component
            })
            cluster_idx += 1

    return RelationshipResult(candidate_edges=candidate_edges, clusters=clusters)


def embed_query(query: str) -> list[float] | None:
    """Generates a 384-d vector embedding for search queries."""
    if not query:
        return None
    cleaned = clean_main_content(query)
    vec, _ = generate_embedding(cleaned)
    return vec
