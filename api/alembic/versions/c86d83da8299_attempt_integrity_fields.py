"""attempt integrity fields

Revision ID: c86d83da8299
Revises: d1ef8760b907
Create Date: 2025-08-30 11:16:45.887291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c86d83da8299'
down_revision: Union[str, None] = 'd1ef8760b907'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
