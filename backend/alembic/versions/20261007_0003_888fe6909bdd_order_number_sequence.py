"""order number sequence

Revision ID: 888fe6909bdd
Revises: a9a0f533d249
Create Date: 2026-10-07 00:03:05.525247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '888fe6909bdd'
down_revision: Union[str, Sequence[str], None] = 'a9a0f533d249'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Sequence for server-generated order numbers (ORD-20001, ORD-20002, ...)."""
    op.execute(sa.schema.CreateSequence(sa.Sequence("order_number_seq", start=20001)))


def downgrade() -> None:
    op.execute(sa.schema.DropSequence(sa.Sequence("order_number_seq")))
