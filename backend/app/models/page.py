from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Computed, DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("workspace_id", "canonical_url", name="uq_pages_workspace_canonical_url"),
        UniqueConstraint("workspace_id", "id", name="uq_pages_workspace_id"),
        CheckConstraint("status IN ('discovered','extracting','extracted','processing','ready','extraction_failed','processing_failed')", name="ck_pages_status"),
        CheckConstraint("importance IS NULL OR importance BETWEEN 1 AND 5", name="ck_pages_importance"),
        Index("ix_pages_workspace_status", "workspace_id", "status"),
        Index("ix_pages_workspace_domain", "workspace_id", "domain"),
        Index("ix_pages_search_tsv", "search_tsv", postgresql_using="gin"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(Text)
    favicon_url: Mapped[str | None] = mapped_column(Text)
    og_image_url: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    text: Mapped[str | None] = mapped_column(Text)
    search_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english'::regconfig, coalesce(title, '') || ' ' || coalesce(url, '') || ' ' || coalesce(text, ''))", persisted=True),
    )
    content_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    pos_x: Mapped[float | None] = mapped_column(Float)
    pos_y: Mapped[float | None] = mapped_column(Float)
    importance: Mapped[int | None] = mapped_column(Integer)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
