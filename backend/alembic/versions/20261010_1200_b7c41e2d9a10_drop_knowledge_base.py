"""drop knowledge base

The AI assistant and its knowledge base were removed from the product, and the initial schema
no longer creates the `documents` table or the pgvector extension. Databases created before
that change still have both: drop them there. On a fresh database this is a no-op.

Revision ID: b7c41e2d9a10
Revises: 550953e34734
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b7c41e2d9a10'
down_revision: Union[str, Sequence[str], None] = '550953e34734'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP EXTENSION IF EXISTS vector")


def downgrade() -> None:
    """Downgrade schema."""
    # Nothing to restore: the earlier revisions no longer define these objects.
    pass
