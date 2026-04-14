"""maintenance_plan: add summary field

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("maintenance_plans", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("maintenance_plans", "summary")
