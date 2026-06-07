"""GUSTO Migration: Replace panel credentials with API token

Revision ID: 001_replace_panel_creds_with_token
Revises: 
Create Date: 2026-06-07 23:24:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001_replace_panel_creds_with_token'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new column
    op.add_column('gusto_servers', sa.Column('panel_api_token', sa.Text(), nullable=True))

    # Migrate data: if old credentials exist, set placeholder
    op.execute("""
        UPDATE gusto_servers 
        SET panel_api_token = 'MIGRATE_MANUALLY'
        WHERE panel_username IS NOT NULL OR panel_password IS NOT NULL
    """)

    # Drop old columns
    op.drop_column('gusto_servers', 'panel_username')
    op.drop_column('gusto_servers', 'panel_password')


def downgrade():
    op.add_column('gusto_servers', sa.Column('panel_password', sa.Text(), nullable=True))
    op.add_column('gusto_servers', sa.Column('panel_username', sa.String(length=255), nullable=True))
    op.drop_column('gusto_servers', 'panel_api_token')
