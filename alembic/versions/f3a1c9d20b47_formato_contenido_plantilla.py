"""formato_estandar: guardar contenido de la plantilla para previsualizar

Revision ID: f3a1c9d20b47
Revises: adb21810f740
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1c9d20b47'
down_revision: Union[str, None] = 'adb21810f740'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('formato_estandar', sa.Column('nombre_archivo', sa.String(length=255), nullable=True))
    op.add_column('formato_estandar', sa.Column('content_type', sa.String(length=120), nullable=True))
    op.add_column('formato_estandar', sa.Column('contenido', sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column('formato_estandar', 'contenido')
    op.drop_column('formato_estandar', 'content_type')
    op.drop_column('formato_estandar', 'nombre_archivo')
