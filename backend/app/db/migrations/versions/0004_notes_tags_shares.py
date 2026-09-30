"""Add workspace notes, tags, taggings, and share links."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_notes_tags_shares"
down_revision = "0003_live_processing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text()),
        sa.Column("author", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_type IN ('page','group')", name="ck_notes_target_type"),
        sa.CheckConstraint("kind IN ('note','highlight','comment')", name="ck_notes_kind"),
    )
    op.create_index("ix_notes_workspace_target", "notes", ["workspace_id", "target_type", "target_id"])
    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=False),
    )
    op.create_index("uq_tags_workspace_lower_name", "tags", ["workspace_id", sa.text("lower(name)")], unique=True)
    op.create_table(
        "taggings",
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("target_type", sa.Text(), primary_key=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.CheckConstraint("target_type IN ('page','group')", name="ck_taggings_target_type"),
    )
    op.create_table(
        "share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("token", name="uq_share_links_token"),
        sa.CheckConstraint("role IN ('view','edit')", name="ck_share_links_role"),
    )


def downgrade() -> None:
    op.drop_table("share_links")
    op.drop_table("taggings")
    op.drop_index("uq_tags_workspace_lower_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_notes_workspace_target", table_name="notes")
    op.drop_table("notes")
