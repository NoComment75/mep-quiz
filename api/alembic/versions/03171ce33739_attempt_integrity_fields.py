"""attempt integrity fields

Revision ID: 03171ce33739
Revises: c86d83da8299
Create Date: 2025-08-30 11:18:05.320697
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "03171ce33739"
down_revision: Union[str, None] = "c86d83da8299"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Ensure the PostgreSQL ENUM type exists and contains the values we use
    #    We only need 'in_progress' and 'completed' for the app. If the enum
    #    already exists with extra values (e.g. 'submitted', 'expired'), we keep
    #    them — we only ensure 'completed' is available.
    op.execute(
        """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'attemptstatusenum'
    ) THEN
        CREATE TYPE attemptstatusenum AS ENUM ('in_progress', 'completed');
    END IF;
END $$;
"""
    )

    # Add 'completed' value if it's missing.
    op.execute(
        """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_type t
          JOIN pg_enum e ON e.enumtypid = t.oid
         WHERE t.typname = 'attemptstatusenum'
           AND e.enumlabel = 'completed'
    ) THEN
        ALTER TYPE attemptstatusenum ADD VALUE 'completed';
    END IF;
END $$;
"""
    )

    # 2) Add columns (idempotent) and backfill
    # question_ids: JSONB, status: attemptstatusenum NOT NULL,
    # started_at: timestamp NOT NULL, completed_at: timestamp NULL
    op.execute("ALTER TABLE quiz_attempts ADD COLUMN IF NOT EXISTS question_ids JSONB")
    op.execute("ALTER TABLE quiz_attempts ADD COLUMN IF NOT EXISTS status attemptstatusenum")
    op.execute(
        "ALTER TABLE quiz_attempts ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE quiz_attempts ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITHOUT TIME ZONE"
    )

    # Backfill status and started_at for existing rows
    op.execute(
        "UPDATE quiz_attempts SET status = 'in_progress' WHERE status IS NULL"
    )
    op.execute(
        "UPDATE quiz_attempts SET started_at = COALESCE(started_at, created_at, NOW()) WHERE started_at IS NULL"
    )

    # Enforce NOT NULL where required
    op.execute("ALTER TABLE quiz_attempts ALTER COLUMN status SET NOT NULL")
    op.execute("ALTER TABLE quiz_attempts ALTER COLUMN started_at SET NOT NULL")

    # Helpful index on created_at (if your schema doesn't already have one)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_quiz_attempts_created_at ON quiz_attempts (created_at)"
    )


def downgrade() -> None:
    # Drop the helper index (if present)
    op.execute("DROP INDEX IF EXISTS ix_quiz_attempts_created_at")

    # Drop the added columns (if present)
    op.execute("ALTER TABLE quiz_attempts DROP COLUMN IF EXISTS completed_at")
    op.execute("ALTER TABLE quiz_attempts DROP COLUMN IF EXISTS started_at")
    op.execute("ALTER TABLE quiz_attempts DROP COLUMN IF EXISTS status")
    op.execute("ALTER TABLE quiz_attempts DROP COLUMN IF EXISTS question_ids")

    # We intentionally DO NOT drop the ENUM type 'attemptstatusenum' to avoid
    # breaking other migrations or historical data. If you ever need to remove
    # it, create a dedicated migration to ensure no columns still depend on it.
