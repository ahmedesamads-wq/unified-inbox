"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('owner', 'member', name='userrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create email_accounts table
    op.create_table(
        'email_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.Enum('gmail', 'outlook', name='emailprovider'), nullable=False),
        sa.Column('email_address', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_accounts_email_address'), 'email_accounts', ['email_address'], unique=False)
    op.create_index(op.f('ix_email_accounts_id'), 'email_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_email_accounts_user_id'), 'email_accounts', ['user_id'], unique=False)

    # Create threads table
    op.create_table(
        'threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('provider_thread_id', sa.String(), nullable=False),
        sa.Column('subject', sa.Text(), nullable=True),
        sa.Column('snippet', sa.Text(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['email_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_threads_account_id'), 'threads', ['account_id'], unique=False)
    op.create_index(op.f('ix_threads_id'), 'threads', ['id'], unique=False)
    op.create_index(op.f('ix_threads_last_message_at'), 'threads', ['last_message_at'], unique=False)
    op.create_index(op.f('ix_threads_provider_thread_id'), 'threads', ['provider_thread_id'], unique=False)

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('provider_message_id', sa.String(), nullable=False),
        sa.Column('from_addr', sa.String(), nullable=False),
        sa.Column('to_addrs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('cc_addrs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('bcc_addrs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('subject', sa.Text(), nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('has_attachments', sa.Boolean(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_date'), 'messages', ['date'], unique=False)
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
    op.create_index(op.f('ix_messages_provider_message_id'), 'messages', ['provider_message_id'], unique=True)
    op.create_index(op.f('ix_messages_thread_id'), 'messages', ['thread_id'], unique=False)

    # Create attachments table
    op.create_table(
        'attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('provider_attachment_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attachments_id'), 'attachments', ['id'], unique=False)
    op.create_index(op.f('ix_attachments_message_id'), 'attachments', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_attachments_message_id'), table_name='attachments')
    op.drop_index(op.f('ix_attachments_id'), table_name='attachments')
    op.drop_table('attachments')
    
    op.drop_index(op.f('ix_messages_thread_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_provider_message_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_date'), table_name='messages')
    op.drop_table('messages')
    
    op.drop_index(op.f('ix_threads_provider_thread_id'), table_name='threads')
    op.drop_index(op.f('ix_threads_last_message_at'), table_name='threads')
    op.drop_index(op.f('ix_threads_id'), table_name='threads')
    op.drop_index(op.f('ix_threads_account_id'), table_name='threads')
    op.drop_table('threads')
    
    op.drop_index(op.f('ix_email_accounts_user_id'), table_name='email_accounts')
    op.drop_index(op.f('ix_email_accounts_id'), table_name='email_accounts')
    op.drop_index(op.f('ix_email_accounts_email_address'), table_name='email_accounts')
    op.drop_table('email_accounts')
    
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
