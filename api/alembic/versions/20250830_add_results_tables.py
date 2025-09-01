"""Initial results tables (no-op on existing DB)

Revision ID: 20250830_add_results_tables
Revises: 
Create Date: 2025-08-30

This migration originally created quiz_attempts / quiz_answers, but the
tables already exist in the live DB. We keep this revision as a model
snapshot only so Alembic history can be merged cleanly.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250830_add_results_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: tables already exist in the database.
    pass


def downgrade() -> None:
    # No-op
    pass
