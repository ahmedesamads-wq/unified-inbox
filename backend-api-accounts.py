from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from src.database import get_db
from src.models.email_account import EmailAccount
from src.models.user import User
from src.api.deps import get_current_user
from src.schemas import EmailAccount as EmailAccountSchema
from src.tasks.sync_tasks import sync_account_task

router = APIRouter()


@router.get("/", response_model=List[EmailAccountSchema])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all connected email accounts for current user"""
    result = await db.execute(
        select(EmailAccount)
        .where(EmailAccount.user_id == current_user.id)
        .order_by(EmailAccount.created_at.desc())
    )
    accounts = result.scalars().all()
    return accounts


@router.get("/{account_id}", response_model=EmailAccountSchema)
async def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific email account"""
    result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete/disconnect an email account"""
    result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    await db.delete(account)
    await db.commit()
    
    return {"status": "deleted", "account_id": account_id}


@router.post("/{account_id}/sync")
async def trigger_sync(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger sync for an account"""
    result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Trigger sync task
    task = sync_account_task.delay(account_id)
    
    return {"status": "sync_triggered", "task_id": task.id}
