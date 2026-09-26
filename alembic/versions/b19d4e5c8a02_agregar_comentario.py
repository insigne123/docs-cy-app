"""agregar tabla comentario (notas libres en contratos y licitaciones)

Revision ID: b19d4e5c8a02
Revises: a7c92e6f10d3
Create Date: 2026-09-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b19d4e5c8a02'
down_revision: Union[str, None] = 'a7c92e6f10d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comentario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entidad_tipo', sa.String(length=20), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('creado_en', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_comentario_entidad', 'comentario', ['entidad_tipo', 'entidad_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_comentario_entidad', table_name='comentario')
    op.drop_table('comentario')
