"""Add the live event log, jobs, and future graph/analysis storage."""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_live_processing"
down_revision = "0002_ingest_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "page_analysis",
        sa.Column("page_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("summary", sa.Text()),
        sa.Column("summary_method", sa.Text()),
        sa.Column("keywords", postgresql.JSONB(), nullable=False),
        sa.Column("simhash", sa.Text()),
        sa.Column("embedding", Vector(384)),
        sa.Column("embedding_model", sa.Text()),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_page_analysis_embedding_hnsw", "page_analysis", ["embedding"], postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})
    op.create_table(
        "edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("label", sa.Text()),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id", "source_page_id"], ["pages.workspace_id", "pages.id"], ondelete="CASCADE", name="fk_edges_source_workspace"),
        sa.ForeignKeyConstraint(["workspace_id", "target_page_id"], ["pages.workspace_id", "pages.id"], ondelete="CASCADE", name="fk_edges_target_workspace"),
        sa.UniqueConstraint("workspace_id", "source_page_id", "target_page_id", "type", name="uq_edges_workspace_pair_type"),
        sa.CheckConstraint("source_page_id <> target_page_id", name="ck_edges_distinct_pages"),
        sa.CheckConstraint("type IN ('related_to','source_of','answers','supports','references','navigated_to','duplicate_of','custom')", name="ck_edges_type"),
        sa.CheckConstraint("origin IN ('suggested','manual')", name="ck_edges_origin"),
        sa.CheckConstraint("status IN ('suggested','accepted','rejected')", name="ck_edges_status"),
        sa.CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 1", name="ck_edges_confidence"),
    )
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("keywords", postgresql.JSONB()),
        sa.Column("collapsed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("category IN ('topic','source','importance','custom')", name="ck_groups_category"),
        sa.CheckConstraint("origin IN ('suggested','manual')", name="ck_groups_origin"),
        sa.CheckConstraint("status IN ('suggested','accepted')", name="ck_groups_status"),
    )
    op.create_table(
        "group_members",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("origin IN ('suggested','manual')", name="ck_group_members_origin"),
    )
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True)),
        sa.Column("state", sa.Text(), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["workspace_id", "page_id"], ["pages.workspace_id", "pages.id"], ondelete="CASCADE", name="fk_jobs_page_workspace"),
        sa.CheckConstraint("kind IN ('analyze_page','recompute_graph')", name="ck_jobs_kind"),
        sa.CheckConstraint("state IN ('queued','running','done','failed')", name="ck_jobs_state"),
    )
    op.create_table(
        "event_log",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("seq", sa.Integer(), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("event_log")
    op.drop_table("processing_jobs")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("edges")
    op.drop_index("ix_page_analysis_embedding_hnsw", table_name="page_analysis")
    op.drop_table("page_analysis")
