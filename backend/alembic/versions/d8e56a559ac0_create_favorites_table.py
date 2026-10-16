"""create favorites table

Revision ID: d8e56a559ac0
Revises: 7fbe46751c72
Create Date: 2026-10-14 20:53:54.025922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8e56a559ac0'
down_revision: Union[str, Sequence[str], None] = '7fbe46751c72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the favorites table."""

    op.create_table(
        "favorites",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "user_email",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "ticker",
            sa.String(length=10),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.UniqueConstraint(
            "user_email",
            "ticker",
            name="uq_favorites_user_ticker",
        ),
    )

    op.create_index(
        "ix_favorites_user_email",
        "favorites",
        ["user_email"],
    )


def downgrade() -> None:
    """Remove the favorites table."""

    op.drop_index(
        "ix_favorites_user_email",
        table_name="favorites",
    )

    op.drop_table("favorites")
