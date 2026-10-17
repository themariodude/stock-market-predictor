"""merge favorites and password reset migration heads

Revision ID: c6d4f7541a0b
Revises: d8e56a559ac0, b30f20261015
Create Date: 2026-10-16 01:49:26.072165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d4f7541a0b'
down_revision: Union[str, Sequence[str], None] = ('d8e56a559ac0', 'b30f20261015')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
