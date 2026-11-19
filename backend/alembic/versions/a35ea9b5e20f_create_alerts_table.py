"""create alerts table

Revision ID: a35ea9b5e20f
Revises: c6d4f7541a0b
Create Date: 2026-11-18 05:45:49.653087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a35ea9b5e20f'
down_revision: Union[str, Sequence[str], None] = 'c6d4f7541a0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
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
            "condition",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "threshold",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_alerts_user_email",
        "alerts",
        ["user_email"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_alerts_user_email",
        table_name="alerts",
    )

    op.drop_table("alerts")