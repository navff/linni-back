"""car: add engine_type field

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cars", sa.Column("engine_type", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cars", "engine_type")
