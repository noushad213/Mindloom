import re
import shlex
from html import escape
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedSearch:
    text: str
    tags: tuple[str, ...]
    domains: tuple[str, ...]


def parse_search(query: str) -> ParsedSearch:
    try:
        tokens = shlex.split(query)
    except ValueError as exc:
        raise ValueError("Unclosed search quote") from exc
    words: list[str] = []
    tags: list[str] = []
    domains: list[str] = []
    for token in tokens:
        if token.startswith("#") and len(token) > 1:
            tags.append(token[1:].lower())
        elif token.startswith("@") and len(token) > 1:
            domains.append(token[1:].lower())
        else:
            words.append(token)
    return ParsedSearch(" ".join(words), tuple(tags), tuple(domains))


def snippet(value: str | None, terms: str, width: int = 160) -> str:
    if not value:
        return ""
    flat = " ".join(value.split())
    if not terms:
        return escape(flat[:width])
    first = terms.split()[0]
    match = re.search(re.escape(first), flat, re.IGNORECASE)
    if match is None:
        return escape(flat[:width])
    start = max(0, match.start() - 45)
    end = min(len(flat), start + width)
    excerpt = flat[start:end]
    match_in_excerpt = re.search(re.escape(first), excerpt, re.IGNORECASE)
    if match_in_excerpt is None:
        return escape(excerpt)
    return (escape(excerpt[:match_in_excerpt.start()]) + "<mark>" +
            escape(match_in_excerpt.group()) + "</mark>" + escape(excerpt[match_in_excerpt.end():]))
