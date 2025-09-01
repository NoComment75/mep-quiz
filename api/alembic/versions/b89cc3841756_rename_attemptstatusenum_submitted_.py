"""rename attemptstatusenum submitted->completed

Revision ID: b89cc3841756
Revises: 03171ce33739
Create Date: 2025-08-30 13:02:15.948912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b89cc3841756'
down_revision: Union[str, None] = '03171ce33739'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
