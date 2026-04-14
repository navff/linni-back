"""maintenance_plan: replace interval/last fields with target_km/target_date

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Удаляем старые колонки периодичности и последнего выполнения
    op.drop_column("maintenance_plans", "interval_km")
    op.drop_column("maintenance_plans", "interval_months")
    op.drop_column("maintenance_plans", "last_mileage")
    op.drop_column("maintenance_plans", "last_date")

    # Добавляем колонки целевых значений
    op.add_column("maintenance_plans", sa.Column("target_km", sa.Integer(), nullable=True))
    op.add_column("maintenance_plans", sa.Column("target_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("maintenance_plans", "target_km")
    op.drop_column("maintenance_plans", "target_date")

    op.add_column("maintenance_plans", sa.Column("last_date", sa.Date(), nullable=True))
    op.add_column("maintenance_plans", sa.Column("last_mileage", sa.Integer(), nullable=True))
    op.add_column("maintenance_plans", sa.Column("interval_months", sa.Integer(), nullable=True))
    op.add_column("maintenance_plans", sa.Column("interval_km", sa.Integer(), nullable=True))
