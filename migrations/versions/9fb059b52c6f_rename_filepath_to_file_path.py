"""rename filepath to file_path

Revision ID: 9fb059b52c6f
Revises: be3c66542af8
Create Date: 2026-07-09 15:40:37.093089

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fb059b52c6f'
down_revision: Union[str, None] = 'be3c66542af8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('resumes', 'filepath', new_column_name='file_path')


def downgrade() -> None:
    op.alter_column('resumes', 'file_path', new_column_name='filepath')
