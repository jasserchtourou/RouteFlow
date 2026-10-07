"""exception resolution note and active uniqueness

Revision ID: 7e696cba5c3b
Revises: 9d3450f689c6
Create Date: 2026-10-07 14:53:45.823302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e696cba5c3b'
down_revision: Union[str, Sequence[str], None] = '9d3450f689c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shipment_exceptions', sa.Column('resolution_note', sa.Text(), nullable=True))
    # Data migration: incidents resolved before notes existed get a placeholder, otherwise the
    # constraint below could not be added to databases that already contain data.
    op.execute(
        "UPDATE shipment_exceptions SET resolution_note = 'Resolved before resolution notes "
        "were recorded.' WHERE status = 'RESOLVED' AND resolution_note IS NULL"
    )
    # Not detected by autogenerate (Alembic does not compare CHECK constraints): added by hand.
    op.create_check_constraint(
        op.f('ck_shipment_exceptions_resolution_note_when_resolved'),
        'shipment_exceptions',
        "status <> 'RESOLVED' OR resolution_note IS NOT NULL",
    )
    op.create_index(
        'uq_shipment_exceptions_active_type',
        'shipment_exceptions',
        ['shipment_id', 'type'],
        unique=True,
        postgresql_where=sa.text("status <> 'RESOLVED'"),
    )


def downgrade() -> None:
    op.drop_index('uq_shipment_exceptions_active_type', table_name='shipment_exceptions')
    op.drop_constraint(
        op.f('ck_shipment_exceptions_resolution_note_when_resolved'),
        'shipment_exceptions',
        type_='check',
    )
    op.drop_column('shipment_exceptions', 'resolution_note')
