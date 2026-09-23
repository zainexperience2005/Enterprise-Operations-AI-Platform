"""add investigation lifecycle fields

Revision ID: 21414af8f508
Revises: fbfa83dcd67d
Create Date: 2026-09-23 12:48:13.138757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21414af8f508'
down_revision: Union[str, Sequence[str], None] = 'fbfa83dcd67d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "investigations",
        sa.Column(
            "thread_id",
            sa.String(),
            nullable=True,
        ),
    )
    op.add_column(
        "investigations",
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("investigations", "completed_at")
    op.drop_column("investigations", "thread_id")
