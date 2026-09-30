from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TabSession(Base):
    __tablename__ = "tab_sessions"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "page_id"], ["pages.workspace_id", "pages.id"], ondelete="CASCADE", name="fk_tab_sessions_page_workspace"),
        UniqueConstraint("workspace_id", "browser_tab_id", "page_id", name="uq_tab_sessions_workspace_tab_page"),
        CheckConstraint("state IN ('open','closed')", name="ck_tab_sessions_state"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    page_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    browser_tab_id: Mapped[int] = mapped_column(Integer, nullable=False)
    window_id: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="open", server_default=text("'open'"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
