"""add portfolio instrument sort order

Revision ID: 0002_portfolio_instrument_sort_order
Revises: 0001_initial
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_sort_order"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portfolio_instruments", sa.Column("sort_order", sa.Integer(), nullable=True))
    op.execute(
        """
        WITH ordered AS (
            SELECT
                id,
                ROW_NUMBER() OVER (PARTITION BY portfolio_id ORDER BY id) - 1 AS row_order
            FROM portfolio_instruments
        )
        UPDATE portfolio_instruments
        SET sort_order = ordered.row_order
        FROM ordered
        WHERE portfolio_instruments.id = ordered.id
        """
    )
    op.alter_column(
        "portfolio_instruments",
        "sort_order",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("0"),
    )


def downgrade() -> None:
    op.drop_column("portfolio_instruments", "sort_order")
