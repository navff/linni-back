"""add fuel record fields

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the mileage > 0 check so fuel records can have NULL mileage
    op.drop_constraint("service_records_mileage_positive", "service_records", type_="check")

    # Make mileage nullable for fuel records
    op.alter_column("service_records", "mileage", nullable=True)

    # record_type: 'service' (default) or 'fuel'
    op.add_column(
        "service_records",
        sa.Column("record_type", sa.Text(), nullable=False, server_default="service"),
    )
    op.add_column(
        "service_records",
        sa.Column("fuel_liters", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "service_records",
        sa.Column("consumption_per_100km", sa.Numeric(5, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("service_records", "consumption_per_100km")
    op.drop_column("service_records", "fuel_liters")
    op.drop_column("service_records", "record_type")
    op.alter_column("service_records", "mileage", nullable=False)
    op.create_check_constraint(
        "service_records_mileage_positive", "service_records", "mileage > 0"
    )
