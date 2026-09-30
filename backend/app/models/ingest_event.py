from uuid import UUID

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestEvent(Base):
    """Stored HTTP result for retry-safe ingestion; never exposed as an API object."""

    __tablename__ = "ingest_events"

    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    client_event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    response_body: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
