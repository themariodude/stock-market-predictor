"""Merge US-39-40 and US-41 alert migrations

Revision ID: 1c969e1fde6f
Revises: a35ea9b5e20f, ed13954f2234
Create Date: 2026-11-19 21:41:31.086903

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c969e1fde6f'
down_revision: Union[str, Sequence[str], None] = ('a35ea9b5e20f', 'ed13954f2234')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
