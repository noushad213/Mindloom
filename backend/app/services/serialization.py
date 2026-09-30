from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Page, PageAnalysis, TabSession, Workspace
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
        tags=[],
        group_ids=[],
        tab_open=tab_open,
        first_seen_at=page.first_seen_at,
        last_seen_at=page.last_seen_at,
        updated_at=page.updated_at,
    ).model_dump(mode="json")


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
