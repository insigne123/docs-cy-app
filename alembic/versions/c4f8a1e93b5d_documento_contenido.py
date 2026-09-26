"""documento: guardar contenido real del archivo para previsualizar

Revision ID: c4f8a1e93b5d
Revises: b19d4e5c8a02
Create Date: 2026-09-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f8a1e93b5d'
down_revision: Union[str, None] = 'b19d4e5c8a02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documento', sa.Column('content_type', sa.String(length=120), nullable=True))
    op.add_column('documento', sa.Column('contenido', sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column('documento', 'contenido')
    op.drop_column('documento', 'content_type')
