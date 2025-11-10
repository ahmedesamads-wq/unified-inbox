from celery import Task
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import asyncio
from src.tasks.celery_app import celery_app
from src.database import AsyncSessionLocal
from src.models.email_account import EmailAccount, EmailProvider
from src.models.thread import Thread
from src.models.message import Message
from src.services.gmail import gmail_service
from src.services.outlook import outlook_service
from src.services.encryption import encryption_service
from src.config import settings
import time


class DatabaseTask(Task):
    """Base task with database session"""
    _session = None

    def get_session(self):
        return AsyncSessionLocal()


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3)
def sync_account_task(self, account_id: int):
    """Sync a single email account"""
    return asyncio.run(sync_account_async(account_id))


async def sync_account_async(account_id: int):
    """Async function to sync account"""
    async with AsyncSessionLocal() as db:
        try:
            # Get account
            result = await db.execute(
                select(EmailAccount).where(EmailAccount.id == account_id)
            )
            account = result.scalar_one_or_none()
            
            if not account or not account.is_active:
                return {'status': 'skipped', 'reason': 'account not found or inactive'}
            
            # Check if token needs refresh
            if account.token_expiry and account.token_expiry < datetime.utcnow():
                await refresh_token(account, db)
            
            # Fetch messages based on provider
            if account.provider == EmailProvider.GMAIL:
                await sync_gmail_account(account, db)
            elif account.provider == EmailProvider.OUTLOOK:
                await sync_outlook_account(account, db)
            
            # Update last synced time
            account.last_synced_at = datetime.utcnow()
            await db.commit()
            
            return {'status': 'success', 'account_id': account_id}
        
        except Exception as e:
            print(f"Error syncing account {account_id}: {str(e)}")
            await db.rollback()
            # Exponential backoff
            raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)


async def refresh_token(account: EmailAccount, db):
    """Refresh access token"""
    if not account.encrypted_refresh_token:
        account.is_active = False
        return
    
    try:
        refresh_token = encryption_service.decrypt(account.encrypted_refresh_token)
        
        if account.provider == EmailProvider.GMAIL:
            tokens = await gmail_service.refresh_access_token(refresh_token)
        elif account.provider == EmailProvider.OUTLOOK:
            tokens = await outlook_service.refresh_access_token(refresh_token)
        else:
            return
        
        account.access_token = tokens['access_token']
        expires_in = tokens.get('expires_in', 3600)
        account.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Update refresh token if new one provided
        if 'refresh_token' in tokens:
            account.encrypted_refresh_token = encryption_service.encrypt(tokens['refresh_token'])
        
        await db.commit()
    
    except Exception as e:
        print(f"Failed to refresh token for account {account.id}: {str(e)}")
        account.is_active = False
        await db.commit()


async def sync_gmail_account(account: EmailAccount, db):
    """Sync Gmail account"""
    try:
        # Get sync state
        sync_state = account.sync_state or {}
        history_id = sync_state.get('history_id')
        
        # Fetch messages
        result = await gmail_service.fetch_messages(
            access_token=account.access_token,
            max_results=settings.MAX_MESSAGES_PER_ACCOUNT,
            history_id=history_id
        )
        
        if result['type'] == 'full':
            # Process full sync
            for msg_data in result.get('messages', []):
                await process_gmail_message(msg_data, account, db)
            
            # Update history_id
            if result.get('history_id'):
                account.sync_state = {'history_id': result['history_id']}
        
        elif result['type'] == 'history':
            # Process incremental sync
            history = result.get('data', {})
            for history_record in history.get('history', []):
                for msg in history_record.get('messagesAdded', []):
                    # Fetch full message
                    # In production, batch these requests
                    pass
        
        await db.commit()
    
    except Exception as e:
        print(f"Gmail sync error for account {account.id}: {str(e)}")
        raise


async def process_gmail_message(msg_data: dict, account: EmailAccount, db):
    """Process and store Gmail message"""
    parsed = gmail_service.parse_message(msg_data)
    
    # Check if message already exists
    result = await db.execute(
        select(Message).where(Message.provider_message_id == parsed['provider_message_id'])
    )
    if result.scalar_one_or_none():
        return  # Already synced
    
    # Get or create thread
    result = await db.execute(
        select(Thread).where(
            and_(
                Thread.account_id == account.id,
                Thread.provider_thread_id == parsed['thread_id']
            )
        )
    )
    thread = result.scalar_one_or_none()
    
    if not thread:
        thread = Thread(
            account_id=account.id,
            provider_thread_id=parsed['thread_id'],
            subject=parsed['subject'],
            snippet=parsed['snippet'],
            last_message_at=parsed['date']
        )
        db.add(thread)
        await db.flush()
    else:
        # Update thread
        if parsed['date'] > thread.last_message_at:
            thread.last_message_at = parsed['date']
            thread.snippet = parsed['snippet']
    
    # Create message
    message = Message(
        thread_id=thread.id,
        provider_message_id=parsed['provider_message_id'],
        from_addr=parsed['from_addr'],
        to_addrs=parsed['to_addrs'],
        cc_addrs=parsed.get('cc_addrs', []),
        subject=parsed['subject'],
        date=parsed['date'],
        body_text=parsed.get('body_text'),
        body_html=parsed.get('body_html'),
        has_attachments=parsed['has_attachments']
    )
    db.add(message)
    await db.flush()
    
    # Store attachments metadata
    from src.models.message import Attachment
    for att in parsed.get('attachments', []):
        attachment = Attachment(
            message_id=message.id,
            filename=att['filename'],
            size=att.get('size'),
            mime_type=att.get('mime_type'),
            provider_attachment_id=att['attachment_id']
        )
        db.add(attachment)


async def sync_outlook_account(account: EmailAccount, db):
    """Sync Outlook account"""
    try:
        # Get sync state
        sync_state = account.sync_state or {}
        delta_link = sync_state.get('delta_link')
        
        # Fetch messages
        result = await outlook_service.fetch_messages(
            access_token=account.access_token,
            max_results=settings.MAX_MESSAGES_PER_ACCOUNT,
            delta_link=delta_link
        )
        
        # Process messages
        for msg_data in result.get('messages', []):
            await process_outlook_message(msg_data, account, db)
        
        # Update delta link
        if result.get('delta_link'):
            account.sync_state = {'delta_link': result['delta_link']}
        
        await db.commit()
    
    except Exception as e:
        print(f"Outlook sync error for account {account.id}: {str(e)}")
        raise


async def process_outlook_message(msg_data: dict, account: EmailAccount, db):
    """Process and store Outlook message"""
    parsed = outlook_service.parse_message(msg_data)
    
    # Check if message already exists
    result = await db.execute(
        select(Message).where(Message.provider_message_id == parsed['provider_message_id'])
    )
    if result.scalar_one_or_none():
        return  # Already synced
    
    # Get or create thread
    result = await db.execute(
        select(Thread).where(
            and_(
                Thread.account_id == account.id,
                Thread.provider_thread_id == parsed['thread_id']
            )
        )
    )
    thread = result.scalar_one_or_none()
    
    if not thread:
        thread = Thread(
            account_id=account.id,
            provider_thread_id=parsed['thread_id'],
            subject=parsed['subject'],
            snippet=parsed['snippet'],
            last_message_at=parsed['date']
        )
        db.add(thread)
        await db.flush()
    else:
        # Update thread
        if parsed['date'] > thread.last_message_at:
            thread.last_message_at = parsed['date']
            thread.snippet = parsed['snippet']
    
    # Create message
    message = Message(
        thread_id=thread.id,
        provider_message_id=parsed['provider_message_id'],
        from_addr=parsed['from_addr'],
        to_addrs=parsed['to_addrs'],
        cc_addrs=parsed.get('cc_addrs', []),
        subject=parsed['subject'],
        date=parsed['date'],
        body_text=parsed.get('body_text'),
        body_html=parsed.get('body_html'),
        has_attachments=parsed['has_attachments']
    )
    db.add(message)
    await db.flush()
    
    # Store attachments metadata
    from src.models.message import Attachment
    for att in parsed.get('attachments', []):
        attachment = Attachment(
            message_id=message.id,
            filename=att['filename'],
            size=att.get('size'),
            mime_type=att.get('mime_type'),
            provider_attachment_id=att['attachment_id']
        )
        db.add(attachment)


@celery_app.task
def sync_all_accounts():
    """Sync all active accounts"""
    return asyncio.run(sync_all_accounts_async())


async def sync_all_accounts_async():
    """Async function to sync all accounts"""
    async with AsyncSessionLocal() as db:
        # Get all active accounts
        result = await db.execute(
            select(EmailAccount).where(EmailAccount.is_active == True)
        )
        accounts = result.scalars().all()
        
        # Trigger sync for each account
        for account in accounts:
            sync_account_task.delay(account.id)
        
        return {'status': 'triggered', 'count': len(accounts)}
