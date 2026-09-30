"""Create workspaces, pages, and tab sessions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_core_tables"
down_revision = "0000_enable_vector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("excluded_domains", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("view_state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tracking", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("domain", sa.Text()),
        sa.Column("favicon_url", sa.Text()),
        sa.Column("og_image_url", sa.Text()),
        sa.Column("meta", postgresql.JSONB(), nullable=False),
        sa.Column("text", sa.Text()),
        sa.Column("search_tsv", postgresql.TSVECTOR(), sa.Computed("to_tsvector('english'::regconfig, coalesce(title, '') || ' ' || coalesce(url, '') || ' ' || coalesce(text, ''))", persisted=True)),
        sa.Column("content_hash", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("pos_x", sa.Float()),
        sa.Column("pos_y", sa.Float()),
        sa.Column("importance", sa.Integer()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "canonical_url", name="uq_pages_workspace_canonical_url"),
        sa.UniqueConstraint("workspace_id", "id", name="uq_pages_workspace_id"),
        sa.CheckConstraint("status IN ('discovered','extracting','extracted','processing','ready','extraction_failed','processing_failed')", name="ck_pages_status"),
        sa.CheckConstraint("importance IS NULL OR importance BETWEEN 1 AND 5", name="ck_pages_importance"),
    )
    op.create_index("ix_pages_workspace_status", "pages", ["workspace_id", "status"])
    op.create_index("ix_pages_workspace_domain", "pages", ["workspace_id", "domain"])
    op.create_index("ix_pages_search_tsv", "pages", ["search_tsv"], postgresql_using="gin")
    op.create_table(
        "tab_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("browser_tab_id", sa.Integer(), nullable=False),
        sa.Column("window_id", sa.Integer()),
        sa.Column("state", sa.Text(), nullable=False, server_default=sa.text("'open'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["workspace_id", "page_id"], ["pages.workspace_id", "pages.id"], ondelete="CASCADE", name="fk_tab_sessions_page_workspace"),
        sa.UniqueConstraint("workspace_id", "browser_tab_id", "page_id", name="uq_tab_sessions_workspace_tab_page"),
        sa.CheckConstraint("state IN ('open','closed')", name="ck_tab_sessions_state"),
    )


def downgrade() -> None:
    op.drop_table("tab_sessions")
    op.drop_index("ix_pages_search_tsv", table_name="pages")
    op.drop_index("ix_pages_workspace_domain", table_name="pages")
    op.drop_index("ix_pages_workspace_status", table_name="pages")
    op.drop_table("pages")
    op.drop_table("workspaces")
