from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False)


Index("uq_tags_workspace_lower_name", Tag.workspace_id, func.lower(Tag.name), unique=True)


class Tagging(Base):
    __tablename__ = "taggings"
    __table_args__ = (CheckConstraint("target_type IN ('page','group')", name="ck_taggings_target_type"),)

    tag_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    target_type: Mapped[str] = mapped_column(Text, primary_key=True)
    target_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
