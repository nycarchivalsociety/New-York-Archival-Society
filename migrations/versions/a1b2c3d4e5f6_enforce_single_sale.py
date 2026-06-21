"""enforce single sale per inventory item

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2026-06-20
"""

from alembic import op


revision = "a1b2c3d4e5f6"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_transactions_item_id", "transactions", ["item_id"]
    )
    op.create_unique_constraint(
        "uq_donor_item_item_id", "donor_item", ["item_id"]
    )


def downgrade():
    op.drop_constraint(
        "uq_donor_item_item_id", "donor_item", type_="unique"
    )
    op.drop_constraint(
        "uq_transactions_item_id", "transactions", type_="unique"
    )
