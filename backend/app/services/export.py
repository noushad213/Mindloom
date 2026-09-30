from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Edge, Group, GroupMember, Note, Page, PageAnalysis, Tag, Tagging, Workspace


def export_workspace(db: Session, workspace: Workspace, include_text: bool = False) -> dict:
    pages = db.scalars(select(Page).where(Page.workspace_id == workspace.id).order_by(Page.created_at)).all()
    groups = db.scalars(select(Group).where(Group.workspace_id == workspace.id)).all()
    edges = db.scalars(select(Edge).where(Edge.workspace_id == workspace.id, Edge.status != "rejected")).all()
    notes = db.scalars(select(Note).where(Note.workspace_id == workspace.id)).all()
    page_items = []
    for page in pages:
        analysis = db.get(PageAnalysis, page.id)
        tag_names = db.scalars(select(Tag.name).join(Tagging, Tagging.tag_id == Tag.id).where(
            Tagging.target_type == "page", Tagging.target_id == page.id)).all()
        item = {"id": str(page.id), "url": page.url, "canonical_url": page.canonical_url,
                "title": page.title, "domain": page.domain, "summary": analysis.summary if analysis else None,
                "keywords": analysis.keywords if analysis else [],
                "pos": {"x": page.pos_x, "y": page.pos_y} if page.pos_x is not None and page.pos_y is not None else None,
                "importance": page.importance, "tags": tag_names}
        if include_text:
            item["text"] = page.text
        page_items.append(item)
    return {"schema_version": 1, "exported_at": datetime.now(timezone.utc).isoformat(),
            "workspace": {"name": workspace.name, "settings": workspace.settings, "view_state": workspace.view_state},
            "pages": page_items,
            "groups": [{"id": str(group.id), "name": group.name, "category": group.category, "color": group.color,
                        "origin": group.origin, "page_ids": [str(pid) for pid in db.scalars(select(GroupMember.page_id).where(GroupMember.group_id == group.id)).all()]}
                       for group in groups],
            "edges": [{"source": str(edge.source_page_id), "target": str(edge.target_page_id), "type": edge.type,
                       "label": edge.label, "origin": edge.origin, "status": edge.status,
                       "confidence": edge.confidence, "evidence": edge.evidence} for edge in edges],
            "notes": [{"target_type": note.target_type, "target_id": str(note.target_id), "kind": note.kind,
                       "body": note.body, "quote": note.quote} for note in notes]}


def export_markdown(data: dict) -> str:
    lines = [f"# {data['workspace']['name']}", "", "## Groups", ""]
    page_by_id = {page["id"]: page for page in data["pages"]}
    notes_by_target: dict[tuple[str, str], list[str]] = {}
    for note in data["notes"]:
        notes_by_target.setdefault((note["target_type"], note["target_id"]), []).append(note["body"])
    grouped_pages: set[str] = set()

    def render_page(page: dict) -> None:
        lines.extend([f"- [{page['title'] or page['url']}]({page['url']})"])
        if page["summary"]:
            lines.append(f"  - Summary: {page['summary']}")
        if page["tags"]:
            lines.append("  - Tags: " + ", ".join(f"#{tag}" for tag in page["tags"]))
        for body in notes_by_target.get(("page", page["id"]), []):
            lines.append(f"  - Note: {body}")
        if page.get("text"):
            lines.append(f"  - Text: {page['text']}")

    for group in data["groups"]:
        lines.extend([f"### {group['name']}", ""])
        for body in notes_by_target.get(("group", group["id"]), []):
            lines.extend([f"> {body}", ""])
        for page_id in group["page_ids"]:
            if page_id in page_by_id:
                render_page(page_by_id[page_id])
                grouped_pages.add(page_id)
        lines.append("")
    lines.extend(["## Other pages", ""])
    for page in data["pages"]:
        if page["id"] not in grouped_pages:
            render_page(page)
    lines.append("")
    lines.extend(["## Relationships", ""])
    for edge in data["edges"]:
        source = page_by_id.get(edge["source"])
        target = page_by_id.get(edge["target"])
        if source and target:
            lines.append(f"- {source['title'] or source['url']} **{edge['type']}** {target['title'] or target['url']}")
    return "\n".join(lines) + "\n"
