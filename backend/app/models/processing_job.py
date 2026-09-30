from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "page_id"], ["pages.workspace_id", "pages.id"], ondelete="CASCADE", name="fk_jobs_page_workspace"),
        CheckConstraint("kind IN ('analyze_page','recompute_graph')", name="ck_jobs_kind"),
        CheckConstraint("state IN ('queued','running','done','failed')", name="ck_jobs_state"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    page_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    state: Mapped[str] = mapped_column(Text, nullable=False, default="queued", server_default=text("'queued'"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
