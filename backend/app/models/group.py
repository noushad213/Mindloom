from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (
        CheckConstraint("category IN ('topic','source','importance','custom')", name="ck_groups_category"),
        CheckConstraint("origin IN ('suggested','manual')", name="ck_groups_origin"),
        CheckConstraint("status IN ('suggested','accepted')", name="ck_groups_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str] | None] = mapped_column(JSONB)
    collapsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (CheckConstraint("origin IN ('suggested','manual')", name="ck_group_members_origin"),)

    group_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    page_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
