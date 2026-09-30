from app.services.export import export_markdown
from app.services.search import parse_search, snippet


def test_search_tokens_and_quotes():
    parsed = parse_search('"clinical triage" #Important @Nature.com')
    assert parsed.text == "clinical triage"
    assert parsed.tags == ("important",)
    assert parsed.domains == ("nature.com",)
    assert "<mark>triage</mark>" in snippet("Emergency triage research", "triage")


def test_markdown_export_contains_pages_groups_edges_notes():
    data = {"workspace": {"name": "Research"},
            "pages": [{"id": "a", "title": "Article", "url": "https://example.com", "summary": "Summary",
                       "tags": ["key"]}, {"id": "b", "title": "Follow-up", "url": "https://example.org",
                                           "summary": None, "tags": []}],
            "groups": [{"id": "g", "name": "Sources", "page_ids": ["a"]}],
            "edges": [{"source": "a", "target": "b", "type": "supports"}],
            "notes": [{"target_type": "page", "target_id": "a", "body": "Read again"}]}
    markdown = export_markdown(data)
    assert "[Article](https://example.com)" in markdown
    assert "#key" in markdown
    assert "Article **supports** Follow-up" in markdown
    assert "Read again" in markdown
