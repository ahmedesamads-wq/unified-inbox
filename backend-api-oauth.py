from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from src.database import get_db
from src.models.email_account import EmailAccount, EmailProvider
from src.models.user import User
from src.api.deps import get_current_user
from src.services.gmail import gmail_service
from src.services.outlook import outlook_service
from src.services.encryption import encryption_service
from src.tasks.sync_tasks import sync_account_task
import secrets

router = APIRouter()

# Store state tokens temporarily (in production, use Redis)
oauth_states = {}


@router.get("/gmail/authorize")
async def gmail_authorize(current_user: User = Depends(get_current_user)):
    """Initiate Gmail OAuth flow"""
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {'user_id': current_user.id, 'provider': 'gmail'}
    
    auth_url = gmail_service.get_authorization_url(state)
    return {'authorization_url': auth_url}


@router.get("/gmail/callback")
async def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle Gmail OAuth callback"""
    # Verify state
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    state_data = oauth_states.pop(state)
    user_id = state_data['user_id']
    
    try:
        # Exchange code for tokens
        tokens = await gmail_service.exchange_code_for_tokens(code)
        access_token = tokens['access_token']
        refresh_token = tokens.get('refresh_token')
        expires_in = tokens.get('expires_in', 3600)
        
        # Get user profile
        profile = await gmail_service.get_user_profile(access_token)
        email_address = profile['emailAddress']
        
        # Check if account already exists
        from sqlalchemy import select
        result = await db.execute(
            select(EmailAccount).where(
                EmailAccount.user_id == user_id,
                EmailAccount.email_address == email_address,
                EmailAccount.provider == EmailProvider.GMAIL
            )
        )
        account = result.scalar_one_or_none()
        
        if account:
            # Update existing account
            account.access_token = access_token
            account.encrypted_refresh_token = encryption_service.encrypt(refresh_token) if refresh_token else None
            account.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            account.is_active = True
        else:
            # Create new account
            account = EmailAccount(
                user_id=user_id,
                provider=EmailProvider.GMAIL,
                email_address=email_address,
                display_name=email_address,
                access_token=access_token,
                encrypted_refresh_token=encryption_service.encrypt(refresh_token) if refresh_token else None,
                token_expiry=datetime.utcnow() + timedelta(seconds=expires_in),
                is_active=True
            )
            db.add(account)
        
        await db.commit()
        await db.refresh(account)
        
        # Trigger initial sync
        sync_account_task.delay(account.id)
        
        # Redirect to frontend
        return RedirectResponse(url=f"{settings.BASE_URL}/#/dashboard?connected=gmail")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")


@router.get("/outlook/authorize")
async def outlook_authorize(current_user: User = Depends(get_current_user)):
    """Initiate Outlook OAuth flow"""
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {'user_id': current_user.id, 'provider': 'outlook'}
    
    auth_url = outlook_service.get_authorization_url(state)
    return {'authorization_url': auth_url}


@router.get("/outlook/callback")
async def outlook_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle Outlook OAuth callback"""
    # Verify state
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    state_data = oauth_states.pop(state)
    user_id = state_data['user_id']
    
    try:
        # Exchange code for tokens
        tokens = await outlook_service.exchange_code_for_tokens(code)
        access_token = tokens['access_token']
        refresh_token = tokens.get('refresh_token')
        expires_in = tokens.get('expires_in', 3600)
        
        # Get user profile
        profile = await outlook_service.get_user_profile(access_token)
        email_address = profile['mail'] or profile['userPrincipalName']
        display_name = profile.get('displayName', email_address)
        
        # Check if account already exists
        from sqlalchemy import select
        result = await db.execute(
            select(EmailAccount).where(
                EmailAccount.user_id == user_id,
                EmailAccount.email_address == email_address,
                EmailAccount.provider == EmailProvider.OUTLOOK
            )
        )
        account = result.scalar_one_or_none()
        
        if account:
            # Update existing account
            account.access_token = access_token
            account.encrypted_refresh_token = encryption_service.encrypt(refresh_token) if refresh_token else None
            account.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            account.is_active = True
        else:
            # Create new account
            account = EmailAccount(
                user_id=user_id,
                provider=EmailProvider.OUTLOOK,
                email_address=email_address,
                display_name=display_name,
                access_token=access_token,
                encrypted_refresh_token=encryption_service.encrypt(refresh_token) if refresh_token else None,
                token_expiry=datetime.utcnow() + timedelta(seconds=expires_in),
                is_active=True
            )
            db.add(account)
        
        await db.commit()
        await db.refresh(account)
        
        # Trigger initial sync
        sync_account_task.delay(account.id)
        
        # Redirect to frontend
        from src.config import settings
        return RedirectResponse(url=f"{settings.BASE_URL}/#/dashboard?connected=outlook")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")
