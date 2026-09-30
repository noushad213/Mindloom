"""Record ingest responses for durable client_event_id idempotency."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_ingest_events"
down_revision = "0001_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_events",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("client_event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("response_body", postgresql.JSONB(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ingest_events")
