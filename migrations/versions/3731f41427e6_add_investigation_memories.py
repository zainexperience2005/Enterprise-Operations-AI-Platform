"""add investigation memories

Revision ID: 3731f41427e6
Revises: 21414af8f508
Create Date: 2026-09-23 12:53:13.165909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3731f41427e6'
down_revision: Union[str, Sequence[str], None] = '21414af8f508'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'investigation_memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.String(), nullable=False),
        sa.Column('memory_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investigation_memories_investigation_id'), 'investigation_memories', ['investigation_id'], unique=False)
    op.create_index(op.f('ix_investigation_memories_memory_type'), 'investigation_memories', ['memory_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_investigation_memories_memory_type'), table_name='investigation_memories')
    op.drop_index(op.f('ix_investigation_memories_investigation_id'), table_name='investigation_memories')
    op.drop_table('investigation_memories')
    # ### end Alembic commands ###
