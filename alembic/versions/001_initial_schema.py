"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-02-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create asset_types table
    op.create_table(
        'asset_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asset_types_id'), 'asset_types', ['id'], unique=False)
    op.create_index(op.f('ix_asset_types_code'), 'asset_types', ['code'], unique=True)

    # Create wallets table
    op.create_table(
        'wallets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('asset_type_id', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Numeric(precision=20, scale=2), nullable=False, server_default='0'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_type_id'], ['asset_types.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'asset_type_id', name='uq_user_asset')
    )
    op.create_index(op.f('ix_wallets_id'), 'wallets', ['id'], unique=False)
    op.create_index(op.f('ix_wallets_user_id'), 'wallets', ['user_id'], unique=False)
    op.create_index('idx_wallet_user_asset', 'wallets', ['user_id', 'asset_type_id'], unique=False)

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(length=100), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('transaction_type', sa.Enum('TOPUP', 'BONUS', 'SPEND', 'REFUND', 'ADJUSTMENT', name='transactiontype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'ROLLED_BACK', name='transactionstatus'), nullable=False, server_default='PENDING'),
        sa.Column('from_wallet_id', sa.Integer(), nullable=False),
        sa.Column('to_wallet_id', sa.Integer(), nullable=False),
        sa.Column('asset_type_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('meta_data', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_type_id'], ['asset_types.id']),
        sa.ForeignKeyConstraint(['from_wallet_id'], ['wallets.id']),
        sa.ForeignKeyConstraint(['to_wallet_id'], ['wallets.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index(op.f('ix_transactions_transaction_id'), 'transactions', ['transaction_id'], unique=True)
    op.create_index(op.f('ix_transactions_idempotency_key'), 'transactions', ['idempotency_key'], unique=True)
    op.create_index('idx_transaction_type_status', 'transactions', ['transaction_type', 'status'], unique=False)
    op.create_index('idx_transaction_wallets', 'transactions', ['from_wallet_id', 'to_wallet_id'], unique=False)
    op.create_index('idx_transaction_created', 'transactions', ['created_at'], unique=False)

    # Create ledger_entries table
    op.create_table(
        'ledger_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('wallet_id', sa.Integer(), nullable=False),
        sa.Column('entry_type', sa.Enum('DEBIT', 'CREDIT', name='entrytype'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('balance_after', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id']),
        sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ledger_entries_id'), 'ledger_entries', ['id'], unique=False)
    op.create_index('idx_ledger_wallet_created', 'ledger_entries', ['wallet_id', 'created_at'], unique=False)
    op.create_index('idx_ledger_transaction', 'ledger_entries', ['transaction_id'], unique=False)

    # Create idempotency_logs table
    op.create_table(
        'idempotency_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('request_path', sa.String(length=255), nullable=False),
        sa.Column('request_method', sa.String(length=10), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.String(length=5000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_idempotency_logs_id'), 'idempotency_logs', ['id'], unique=False)
    op.create_index(op.f('ix_idempotency_logs_idempotency_key'), 'idempotency_logs', ['idempotency_key'], unique=True)
    op.create_index('idx_idempotency_expires', 'idempotency_logs', ['expires_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_idempotency_expires', table_name='idempotency_logs')
    op.drop_index(op.f('ix_idempotency_logs_idempotency_key'), table_name='idempotency_logs')
    op.drop_index(op.f('ix_idempotency_logs_id'), table_name='idempotency_logs')
    op.drop_table('idempotency_logs')
    
    op.drop_index('idx_ledger_transaction', table_name='ledger_entries')
    op.drop_index('idx_ledger_wallet_created', table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_id'), table_name='ledger_entries')
    op.drop_table('ledger_entries')
    
    op.drop_index('idx_transaction_created', table_name='transactions')
    op.drop_index('idx_transaction_wallets', table_name='transactions')
    op.drop_index('idx_transaction_type_status', table_name='transactions')
    op.drop_index(op.f('ix_transactions_idempotency_key'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_transaction_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    
    op.drop_index('idx_wallet_user_asset', table_name='wallets')
    op.drop_index(op.f('ix_wallets_user_id'), table_name='wallets')
    op.drop_index(op.f('ix_wallets_id'), table_name='wallets')
    op.drop_table('wallets')
    
    op.drop_index(op.f('ix_asset_types_code'), table_name='asset_types')
    op.drop_index(op.f('ix_asset_types_id'), table_name='asset_types')
    op.drop_table('asset_types')
