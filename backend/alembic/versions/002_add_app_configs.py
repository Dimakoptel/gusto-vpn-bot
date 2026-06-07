"""Add app_configs table for dynamic settings

Revision ID: 002_add_app_configs
Revises: 001_replace_panel_creds_with_token
Create Date: 2024-06-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_app_configs'
down_revision: Union[str, None] = '001_replace_panel_creds_with_token'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'app_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=True),
        sa.Column('is_editable', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index(op.f('ix_app_configs_key'), 'app_configs', ['key'], unique=True)
    op.create_index(op.f('ix_app_configs_category'), 'app_configs', ['category'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_app_configs_category'), table_name='app_configs')
    op.drop_index(op.f('ix_app_configs_key'), table_name='app_configs')
    op.drop_table('app_configs')
