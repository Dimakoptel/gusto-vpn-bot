"""Replace panel credentials with API token + add system_settings table

Revision ID: 001
Revises: 
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_replace_panel_creds_with_token'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add panel_api_token to servers table
    op.add_column('gusto_servers', sa.Column('panel_api_token', sa.Text(), nullable=True))

    # 2. Remove old columns (if exist)
    try:
        op.drop_column('gusto_servers', 'panel_username')
    except Exception:
        pass
    try:
        op.drop_column('gusto_servers', 'panel_password')
    except Exception:
        pass

    # 3. Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bot_token', sa.Text(), nullable=True),
        sa.Column('admin_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('support_username', sa.String(length=255), nullable=True),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('cryptobot_token', sa.Text(), nullable=True),
        sa.Column('cryptobot_enabled', sa.Boolean(), nullable=True),
        sa.Column('yookassa_shop_id', sa.String(length=255), nullable=True),
        sa.Column('yookassa_secret_key', sa.Text(), nullable=True),
        sa.Column('yookassa_enabled', sa.Boolean(), nullable=True),
        sa.Column('yookassa_fiscal_enabled', sa.Boolean(), nullable=True),
        sa.Column('freekassa_id', sa.String(length=255), nullable=True),
        sa.Column('freekassa_secret', sa.Text(), nullable=True),
        sa.Column('freekassa_api_key', sa.Text(), nullable=True),
        sa.Column('freekassa_enabled', sa.Boolean(), nullable=True),
        sa.Column('referral_enabled', sa.Boolean(), nullable=True),
        sa.Column('referral_level1_percent', sa.Float(), nullable=True),
        sa.Column('referral_level2_percent', sa.Float(), nullable=True),
        sa.Column('referral_level3_percent', sa.Float(), nullable=True),
        sa.Column('referral_min_payout', sa.Float(), nullable=True),
        sa.Column('antifraud_enabled', sa.Boolean(), nullable=True),
        sa.Column('antifraud_max_ips', sa.Integer(), nullable=True),
        sa.Column('antifraud_max_countries', sa.Integer(), nullable=True),
        sa.Column('antifraud_ban_hours', sa.Integer(), nullable=True),
        sa.Column('notify_expiry_3days', sa.Boolean(), nullable=True),
        sa.Column('notify_expiry_1day', sa.Boolean(), nullable=True),
        sa.Column('notify_expiry_today', sa.Boolean(), nullable=True),
        sa.Column('notify_low_traffic_gb', sa.Float(), nullable=True),
        sa.Column('notify_channel_id', sa.String(length=255), nullable=True),
        sa.Column('app_name', sa.String(length=255), nullable=True),
        sa.Column('app_logo_url', sa.Text(), nullable=True),
        sa.Column('maintenance_mode', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Insert default settings
    op.execute("""
        INSERT INTO system_settings (id, app_name, maintenance_mode, 
            referral_enabled, referral_level1_percent, referral_level2_percent, referral_level3_percent, referral_min_payout,
            antifraud_enabled, antifraud_max_ips, antifraud_max_countries, antifraud_ban_hours,
            notify_expiry_3days, notify_expiry_1day, notify_expiry_today, notify_low_traffic_gb)
        VALUES (1, 'GUSTO VPN', false,
            true, 30.0, 15.0, 5.0, 500.0,
            true, 3, 2, 24,
            true, true, true, 5.0)
    """)


def downgrade():
    op.drop_table('system_settings')
    op.add_column('gusto_servers', sa.Column('panel_username', sa.String(length=255), nullable=True))
    op.add_column('gusto_servers', sa.Column('panel_password', sa.Text(), nullable=True))
    op.drop_column('gusto_servers', 'panel_api_token')
