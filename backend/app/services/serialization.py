from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Edge, Group, GroupMember, Note, Page, PageAnalysis, TabSession, Tag, Tagging, Workspace
from app.schemas.pages import PageResponse, Position, TabSessionResponse
from app.schemas.workspaces import WorkspaceResponse


def workspace_body(db: Session, workspace: Workspace) -> dict:
    page_count = db.scalar(select(func.count(Page.id)).where(Page.workspace_id == workspace.id)) or 0
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        excluded_domains=workspace.excluded_domains,
        settings=workspace.settings,
        view_state=workspace.view_state,
        tracking=workspace.tracking,
        page_count=page_count,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    ).model_dump(mode="json")


def page_body(db: Session, page: Page) -> dict:
    analysis = db.get(PageAnalysis, page.id)
    tab_open = db.scalar(
        select(TabSession.id).where(TabSession.page_id == page.id, TabSession.state == "open").limit(1)
    ) is not None
    return PageResponse(
        id=page.id,
        workspace_id=page.workspace_id,
        url=page.url,
        canonical_url=page.canonical_url,
        title=page.title,
        domain=page.domain,
        favicon_url=page.favicon_url,
        og_image_url=page.og_image_url,
        summary=analysis.summary if analysis else None,
        keywords=analysis.keywords if analysis else [],
        status=page.status,
        error_code=page.error_code,
        error_message=page.error_message,
        pos=Position(x=page.pos_x, y=page.pos_y) if page.pos_x is not None and page.pos_y is not None else None,
        importance=page.importance,
        tags=[tag_body(tag) for tag in db.scalars(select(Tag).join(Tagging, Tagging.tag_id == Tag.id).where(Tagging.target_type == "page", Tagging.target_id == page.id)).all()],
        group_ids=[str(group_id) for group_id in db.scalars(select(GroupMember.group_id).where(GroupMember.page_id == page.id)).all()],
        tab_open=tab_open,
        first_seen_at=page.first_seen_at,
        last_seen_at=page.last_seen_at,
        updated_at=page.updated_at,
    ).model_dump(mode="json")


def edge_body(edge: Edge) -> dict:
    return {"id": str(edge.id), "source": str(edge.source_page_id), "target": str(edge.target_page_id),
            "type": edge.type, "label": edge.label, "origin": edge.origin, "status": edge.status,
            "confidence": edge.confidence, "evidence": edge.evidence, "updated_at": edge.updated_at.isoformat()}


def group_body(db: Session, group: Group) -> dict:
    return {"id": str(group.id), "name": group.name, "category": group.category, "color": group.color,
            "origin": group.origin, "status": group.status, "keywords": group.keywords or [],
            "page_ids": [str(pid) for pid in db.scalars(select(GroupMember.page_id).where(GroupMember.group_id == group.id)).all()],
            "collapsed": group.collapsed}


def note_body(note: Note) -> dict:
    return {"id": str(note.id), "target_type": note.target_type, "target_id": str(note.target_id),
            "kind": note.kind, "body": note.body, "quote": note.quote, "author": note.author,
            "created_at": note.created_at.isoformat(), "updated_at": note.updated_at.isoformat()}


def tag_body(tag: Tag, count: int | None = None) -> dict:
    body = {"id": str(tag.id), "name": tag.name, "color": tag.color}
    if count is not None:
        body["count"] = count
    return body


def tab_body(tab: TabSession) -> dict:
    return TabSessionResponse(
        id=tab.id,
        page_id=tab.page_id,
        browser_tab_id=tab.browser_tab_id,
        state=tab.state,
        active=tab.active,
        opened_at=tab.opened_at,
        last_seen_at=tab.last_seen_at,
        closed_at=tab.closed_at,
    ).model_dump(mode="json")
