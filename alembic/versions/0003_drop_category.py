"""drop category column

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-13
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("service_records_category_check", "service_records", type_="check")
    op.drop_column("service_records", "category")

    op.drop_constraint("maintenance_plans_category_check", "maintenance_plans", type_="check")
    op.drop_column("maintenance_plans", "category")


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column("service_records", sa.Column("category", sa.Text(), nullable=False, server_default="maintenance"))
    op.create_check_constraint(
        "service_records_category_check",
        "service_records",
        "category IN ('maintenance', 'repair', 'consumable')",
    )

    op.add_column("maintenance_plans", sa.Column("category", sa.Text(), nullable=False, server_default="maintenance"))
    op.create_check_constraint(
        "maintenance_plans_category_check",
        "maintenance_plans",
        "category IN ('maintenance', 'repair', 'consumable')",
    )
