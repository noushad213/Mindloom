from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, ForeignKeyConstraint, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Edge(Base):
    __tablename__ = "edges"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "source_page_id"], ["pages.workspace_id", "pages.id"], ondelete="CASCADE", name="fk_edges_source_workspace"),
        ForeignKeyConstraint(["workspace_id", "target_page_id"], ["pages.workspace_id", "pages.id"], ondelete="CASCADE", name="fk_edges_target_workspace"),
        UniqueConstraint("workspace_id", "source_page_id", "target_page_id", "type", name="uq_edges_workspace_pair_type"),
        CheckConstraint("source_page_id <> target_page_id", name="ck_edges_distinct_pages"),
        CheckConstraint("type IN ('related_to','source_of','answers','supports','references','navigated_to','duplicate_of','custom')", name="ck_edges_type"),
        CheckConstraint("origin IN ('suggested','manual')", name="ck_edges_origin"),
        CheckConstraint("status IN ('suggested','accepted','rejected')", name="ck_edges_status"),
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 1", name="ck_edges_confidence"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    source_page_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    target_page_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
