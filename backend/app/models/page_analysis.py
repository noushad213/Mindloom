from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PageAnalysis(Base):
    __tablename__ = "page_analysis"
    __table_args__ = (Index("ix_page_analysis_embedding_hnsw", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),)

    page_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True)
    summary: Mapped[str | None] = mapped_column(Text)
    summary_method: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    simhash: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    embedding_model: Mapped[str | None] = mapped_column(Text)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
