"""usuario: bloqueo temporal tras intentos de login fallidos

Revision ID: a7c92e6f10d3
Revises: f3a1c9d20b47
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c92e6f10d3'
down_revision: Union[str, None] = 'f3a1c9d20b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuario', sa.Column('intentos_fallidos', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('usuario', sa.Column('bloqueado_hasta', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('usuario', 'bloqueado_hasta')
    op.drop_column('usuario', 'intentos_fallidos')
