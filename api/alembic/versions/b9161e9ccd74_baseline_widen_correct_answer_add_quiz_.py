from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Alembic identifiers
revision = "b9161e9ccd74"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Reuse existing Postgres ENUM; don't create it again
    difficulty_enum = postgresql.ENUM(
        "easy", "medium", "hard",
        name="difficultyenum",
        create_type=False
    )

    # Only create results tables; questions schema already done earlier
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("difficulty", difficulty_enum, nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_attempt_subject_diff_created",
        "quiz_attempts",
        ["subject_id", "difficulty", "created_at"],
    )

    op.create_table(
        "quiz_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(),
                  sa.ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("question_id", sa.Integer(),
                  sa.ForeignKey("questions.id"),
                  nullable=False),
        sa.Column("selected", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("time_taken_seconds", sa.Integer(), nullable=True),
    )

def downgrade():
    op.drop_table("quiz_answers")
    op.drop_index("ix_attempt_subject_diff_created", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
