from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.workspaces import require_workspace
from app.db.session import get_db
from app.intelligence import interface
from app.models import Group, Note, Page, PageAnalysis, Tag, Tagging
from app.services.search import parse_search, snippet


router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/workspaces/{workspace_id}/search")
def search(workspace_id: UUID, q: str = Query(min_length=1),
           scope: Literal["all", "pages", "notes", "tags", "groups"] = "all",
           limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)) -> dict:
    require_workspace(db, workspace_id)
    try:
        parsed = parse_search(q)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    results: list[dict] = []
    page_filters = [Page.workspace_id == workspace_id]
    if parsed.domains:
        page_filters.append(or_(*[func.lower(Page.domain) == domain for domain in parsed.domains]))
    if parsed.tags:
        for name in parsed.tags:
            page_filters.append(Page.id.in_(select(Tagging.target_id).join(Tag, Tag.id == Tagging.tag_id).where(
                Tag.workspace_id == workspace_id, Tagging.target_type == "page", func.lower(Tag.name) == name)))
    filtered_page_ids = None
    if parsed.tags or parsed.domains:
        filtered_page_ids = set(db.scalars(select(Page.id).where(*page_filters)).all())
    if scope in ("all", "pages"):
        scores: dict[UUID, float] = {}
        if parsed.text:
            ts_query = func.websearch_to_tsquery("english", parsed.text)
            for page_id, rank in db.execute(select(Page.id, func.ts_rank(Page.search_tsv, ts_query)).where(
                    *page_filters, Page.search_tsv.op("@@")(ts_query)).limit(limit * 5)):
                scores[page_id] = max(scores.get(page_id, 0.0), 0.5 + float(rank))
            match = f"%{parsed.text}%"
            for page_id, title, summary, keywords in db.execute(select(
                    Page.id, Page.title, PageAnalysis.summary, PageAnalysis.keywords).outerjoin(
                    PageAnalysis, PageAnalysis.page_id == Page.id).where(*page_filters, or_(
                    Page.title.ilike(match), Page.domain.ilike(match), Page.text.ilike(match),
                    PageAnalysis.summary.ilike(match), PageAnalysis.keywords.contains([parsed.text]))).limit(limit * 5)):
                title_text = (title or "").lower()
                score = 1.5 if title_text == parsed.text.lower() else 1.1 if parsed.text.lower() in title_text else 0.65
                if keywords and parsed.text.lower() in {word.lower() for word in keywords}:
                    score = max(score, 1.2)
                scores[page_id] = max(scores.get(page_id, 0.0), score)
            for page_id, tag_name in db.execute(select(Page.id, Tag.name).join(
                    Tagging, (Tagging.target_id == Page.id) & (Tagging.target_type == "page")).join(
                    Tag, Tag.id == Tagging.tag_id).where(*page_filters, Tag.workspace_id == workspace_id,
                    Tag.name.ilike(match)).limit(limit * 5)):
                scores[page_id] = max(scores.get(page_id, 0.0), 1.4 if tag_name.lower() == parsed.text.lower() else 1.0)
            vector = interface.embed_query(parsed.text)
            if vector is not None:
                if len(vector) != 384:
                    raise HTTPException(500, "Query embedding must have 384 dimensions")
                distance = PageAnalysis.embedding.cosine_distance(vector)
                for page_id, d in db.execute(select(Page.id, distance).join(PageAnalysis, PageAnalysis.page_id == Page.id).where(
                        *page_filters, PageAnalysis.embedding.is_not(None)).order_by(distance).limit(limit * 5)):
                    scores[page_id] = max(scores.get(page_id, 0.0), max(0.0, 1.0 - float(d)))
        else:
            for page_id in db.scalars(select(Page.id).where(*page_filters).order_by(Page.last_seen_at.desc()).limit(limit * 5)):
                scores[page_id] = 1.0
        for page_id, score in scores.items():
            page = db.get(Page, page_id)
            analysis = db.get(PageAnalysis, page_id)
            source = next((value for value in (page.title, analysis.summary if analysis else None, page.text)
                           if value and parsed.text.lower() in value.lower()), page.text or page.title)
            results.append({"type": "page", "id": str(page.id), "page_id": str(page.id), "title": page.title or page.url,
                            "snippet": snippet(source, parsed.text), "score": round(score, 4)})
    if parsed.text and scope in ("all", "notes"):
        for note in db.scalars(select(Note).where(Note.workspace_id == workspace_id,
                Note.body.ilike(f"%{parsed.text}%")).limit(limit * 5)).all():
            page_id = note.target_id if note.target_type == "page" else None
            if filtered_page_ids is not None:
                if page_id is None or page_id not in filtered_page_ids:
                    continue
            results.append({"type": "note", "id": str(note.id), "page_id": str(page_id) if page_id else None,
                            "title": "Note", "snippet": snippet(note.body, parsed.text), "score": 0.5})
    if parsed.text and scope in ("all", "tags") and not (parsed.tags or parsed.domains):
        for tag in db.scalars(select(Tag).where(Tag.workspace_id == workspace_id, Tag.name.ilike(f"%{parsed.text}%")).limit(limit)).all():
            results.append({"type": "tag", "id": str(tag.id), "page_id": None, "title": tag.name,
                            "snippet": snippet(tag.name, parsed.text), "score": 0.4})
    if parsed.text and scope in ("all", "groups") and not (parsed.tags or parsed.domains):
        for group in db.scalars(select(Group).where(Group.workspace_id == workspace_id, Group.name.ilike(f"%{parsed.text}%")).limit(limit)).all():
            results.append({"type": "group", "id": str(group.id), "page_id": None, "title": group.name,
                            "snippet": snippet(group.name, parsed.text), "score": 0.4})
    results.sort(key=lambda item: item["score"], reverse=True)
    return {"query": q, "results": results[:limit]}
