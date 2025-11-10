from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from src.database import get_db
from src.models.user import User
from src.models.email_account import EmailAccount, EmailProvider
from src.models.thread import Thread
from src.models.message import Message
from src.api.deps import get_current_user
from src.schemas import InboxMessageSchema, ThreadSchema, MessageSchema, SendMessageRequest
from src.services.gmail import gmail_service
from src.services.outlook import outlook_service

router = APIRouter()


@router.get("/inbox", response_model=List[InboxMessageSchema])
async def get_inbox(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    account_id: Optional[int] = Query(None),
    provider: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0)
):
    """Get unified inbox messages"""
    # Build query
    query = (
        select(Message, Thread, EmailAccount)
        .join(Thread, Message.thread_id == Thread.id)
        .join(EmailAccount, Thread.account_id == EmailAccount.id)
        .where(EmailAccount.user_id == current_user.id)
    )
    
    # Apply filters
    if account_id:
        query = query.where(EmailAccount.id == account_id)
    if provider:
        query = query.where(EmailAccount.provider == provider)
    
    # Order and paginate
    query = query.order_by(Message.date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Transform to response format
    messages = []
    for msg, thread, account in rows:
        messages.append(InboxMessageSchema(
            id=msg.id,
            thread_id=thread.id,
            account_id=account.id,
            account_email=account.email_address,
            provider=account.provider,
            from_addr=msg.from_addr,
            subject=msg.subject,
            snippet=thread.snippet,
            date=msg.date,
            has_attachments=msg.has_attachments,
            is_read=msg.is_read
        ))
    
    return messages


@router.get("/threads/{thread_id}", response_model=ThreadSchema)
async def get_thread(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get thread with all messages"""
    # Get thread
    result = await db.execute(
        select(Thread)
        .join(EmailAccount)
        .where(
            and_(
                Thread.id == thread_id,
                EmailAccount.user_id == current_user.id
            )
        )
    )
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Get messages
    messages_result = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.date.asc())
    )
    messages = messages_result.scalars().all()
    
    # Build response
    return ThreadSchema(
        id=thread.id,
        account_id=thread.account_id,
        provider_thread_id=thread.provider_thread_id,
        subject=thread.subject,
        snippet=thread.snippet,
        last_message_at=thread.last_message_at,
        messages=[MessageSchema.from_orm(msg) for msg in messages]
    )


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send an email from a connected account"""
    # Get account
    result = await db.execute(
        select(EmailAccount).where(
            and_(
                EmailAccount.id == request.account_id,
                EmailAccount.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        # Send via appropriate service
        if account.provider == EmailProvider.GMAIL:
            result = await gmail_service.send_message(
                access_token=account.access_token,
                to=request.to,
                subject=request.subject,
                body_html=request.body_html,
                body_text=request.body_text,
                in_reply_to=request.in_reply_to,
                references=request.references
            )
        elif account.provider == EmailProvider.OUTLOOK:
            result = await outlook_service.send_message(
                access_token=account.access_token,
                to=request.to,
                subject=request.subject,
                body_html=request.body_html,
                body_text=request.body_text,
                in_reply_to=request.in_reply_to
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
        
        return {"status": "sent", "result": result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send: {str(e)}")


@router.get("/{message_id}", response_model=MessageSchema)
async def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific message"""
    result = await db.execute(
        select(Message)
        .join(Thread)
        .join(EmailAccount)
        .where(
            and_(
                Message.id == message_id,
                EmailAccount.user_id == current_user.id
            )
        )
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return message
