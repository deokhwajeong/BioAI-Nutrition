"""Accounts, auth tokens, per-user consent, and daily logs

Revision ID: 3c1a9e2b7d40
Revises: f81b85363b82
Create Date: 2026-10-16 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '3c1a9e2b7d40'
down_revision: Union[str, Sequence[str], None] = 'f81b85363b82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'accounts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('sex', sa.String(), nullable=True),
        sa.Column('activity_level', sa.String(), nullable=True),
    )
    op.create_index('ix_accounts_username', 'accounts', ['username'], unique=True)
    op.create_table(
        'auth_tokens',
        sa.Column('token_hash', sa.String(), primary_key=True),
        sa.Column('account_id', sa.String(), sa.ForeignKey('accounts.id', ondelete='CASCADE')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_auth_tokens_account_id', 'auth_tokens', ['account_id'])
    op.create_table(
        'account_consents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.String(), sa.ForeignKey('accounts.id', ondelete='CASCADE')),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('account_id', 'scope', name='uq_account_scope'),
    )
    op.create_index('ix_account_consents_account_id', 'account_consents', ['account_id'])
    op.create_table(
        'daily_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.String(), sa.ForeignKey('accounts.id', ondelete='CASCADE')),
        sa.Column('date', sa.String(), nullable=False),
        *[
            sa.Column(name, sa.Float(), nullable=True)
            for name in (
                'calories', 'protein_g', 'carbs_g', 'fiber_g', 'sugar_g',
                'omega3_g', 'water_ml', 'steps', 'sleep_hours',
            )
        ],
        sa.UniqueConstraint('account_id', 'date', name='uq_account_date'),
    )
    op.create_index('ix_daily_logs_account_id', 'daily_logs', ['account_id'])


def downgrade() -> None:
    op.drop_table('daily_logs')
    op.drop_table('account_consents')
    op.drop_table('auth_tokens')
    op.drop_index('ix_accounts_username', table_name='accounts')
    op.drop_table('accounts')
