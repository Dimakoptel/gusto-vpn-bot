"""v2.0 — Add plans, update subscriptions, fix payments

Revision ID: 002
Revises: 001
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_add_plans_and_fixes'
down_revision = '001_replace_panel_creds_with_token'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create gusto_plans table
    op.create_table(
        'gusto_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('traffic_gb', sa.Float(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('duration_type', sa.Enum('monthly', 'quarterly', 'semiannual', 'annual', 'custom', name='planduration'), nullable=True),
        sa.Column('device_limit', sa.Integer(), nullable=True),
        sa.Column('ip_limit', sa.Integer(), nullable=True),
        sa.Column('protocol', sa.String(length=20), nullable=True),
        sa.Column('security', sa.String(length=20), nullable=True),
        sa.Column('speed_mbps', sa.Integer(), nullable=True),
        sa.Column('is_premium', sa.Boolean(), nullable=True),
        sa.Column('is_popular', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('target_countries', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('referral_discount_percent', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 2. Add plan_id to gusto_subscriptions if not exists
    try:
        op.add_column('gusto_subscriptions', sa.Column('plan_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_subscriptions_plan', 'gusto_subscriptions', 'gusto_plans', ['plan_id'], ['id'])
    except Exception:
        pass  # May already exist

    # 3. Add payment_method enum values if needed
    # 4. Ensure panel_api_token exists in servers
    try:
        op.add_column('gusto_servers', sa.Column('panel_api_token', sa.Text(), nullable=True))
    except Exception:
        pass

    # 5. Seed default plans
    op.execute("""
        INSERT INTO gusto_plans (name, display_name, description, price, currency, traffic_gb, duration_days, duration_type, device_limit, ip_limit, protocol, security, speed_mbps, is_premium, is_popular, is_active, sort_order, features, referral_discount_percent)
        VALUES 
        ('starter', 'GUSTO Start', 'Базовый тариф для начинающих', 199, 'RUB', 50, 30, 'monthly', 2, 0, 'vless', 'reality', 50, false, false, true, 1, '["VLESS + Reality", "2 устройства", "Базовая поддержка"]', 0),
        ('pro', 'GUSTO Pro', 'Оптимальный выбор для большинства пользователей', 349, 'RUB', 100, 30, 'monthly', 5, 0, 'vless', 'reality', 100, false, true, true, 2, '["VLESS + Reality", "5 устройств", "Приоритетная поддержка", "Smart Router"]', 0),
        ('ultra', 'GUSTO Ultra', 'Максимум возможностей', 599, 'RUB', 200, 30, 'monthly', 10, 0, 'vless', 'reality', 200, true, false, true, 3, '["VLESS + Reality", "10 устройств", "VIP поддержка", "Smart Router", "Premium серверы"]', 0),
        ('quarterly', 'GUSTO 3 месяца', 'Экономия 15%', 899, 'RUB', 300, 90, 'quarterly', 5, 0, 'vless', 'reality', 100, false, false, true, 4, '["VLESS + Reality", "5 устройств", "Экономия 15%", "Smart Router"]', 0),
        ('annual', 'GUSTO 1 год', 'Максимальная экономия — 30%', 2999, 'RUB', 1200, 365, 'annual', 10, 0, 'vless', 'reality', 200, true, false, true, 5, '["VLESS + Reality", "10 устройств", "Экономия 30%", "VIP поддержка", "Premium серверы"]', 0)
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade():
    op.drop_constraint('fk_subscriptions_plan', 'gusto_subscriptions', type_='foreignkey')
    op.drop_column('gusto_subscriptions', 'plan_id')
    op.drop_table('gusto_plans')
