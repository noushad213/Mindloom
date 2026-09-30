"""Enable pgvector before any vector-backed tables exist."""

from alembic import op

revision = "0000_enable_vector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # The extension may be shared by other schemas or applications.
    pass
