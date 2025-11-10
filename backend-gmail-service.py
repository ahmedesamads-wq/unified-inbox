import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import httpx
from src.config import settings


class GmailService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send'
        ]
    
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state
        }
        query = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f'https://accounts.google.com/o/oauth2/v2/auth?{query}'
    
    async def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access and refresh tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'code': code,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'redirect_uri': self.redirect_uri,
                    'grant_type': 'authorization_code'
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'refresh_token': refresh_token,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token'
                }
            )
            response.raise_for_status()
            return response.json()
    
    def _get_service(self, access_token: str):
        """Create Gmail API service client"""
        creds = Credentials(token=access_token)
        return build('gmail', 'v1', credentials=creds)
    
    async def get_user_profile(self, access_token: str) -> Dict:
        """Get user's email address and profile info"""
        service = self._get_service(access_token)
        profile = service.users().getProfile(userId='me').execute()
        return profile
    
    async def fetch_messages(
        self,
        access_token: str,
        max_results: int = 50,
        history_id: Optional[str] = None
    ) -> Dict:
        """Fetch messages from Gmail"""
        service = self._get_service(access_token)
        
        if history_id:
            # Incremental sync using history
            try:
                history = service.users().history().list(
                    userId='me',
                    startHistoryId=history_id,
                    historyTypes=['messageAdded']
                ).execute()
                return {'type': 'history', 'data': history}
            except Exception:
                # If history fails, fall back to full sync
                pass
        
        # Full sync - get recent messages
        messages = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()
        
        message_list = []
        for msg in messages.get('messages', []):
            full_msg = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            message_list.append(full_msg)
        
        # Get current historyId for next sync
        profile = service.users().getProfile(userId='me').execute()
        
        return {
            'type': 'full',
            'messages': message_list,
            'history_id': profile.get('historyId')
        }
    
    def parse_message(self, message: Dict) -> Dict:
        """Parse Gmail message into standardized format"""
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
        
        # Extract body
        body_text = ''
        body_html = ''
        
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body_text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    body_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body_text = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8', errors='ignore')
        
        # Extract attachments
        attachments = []
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part.get('filename') and part.get('body', {}).get('attachmentId'):
                    attachments.append({
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'size': part['body'].get('size', 0),
                        'attachment_id': part['body']['attachmentId']
                    })
        
        # Parse date
        date_str = headers.get('Date', '')
        try:
            from email.utils import parsedate_to_datetime
            date = parsedate_to_datetime(date_str)
        except:
            date = datetime.utcnow()
        
        return {
            'provider_message_id': message['id'],
            'thread_id': message['threadId'],
            'from_addr': headers.get('From', ''),
            'to_addrs': headers.get('To', '').split(','),
            'cc_addrs': headers.get('Cc', '').split(',') if headers.get('Cc') else [],
            'subject': headers.get('Subject', ''),
            'date': date,
            'body_text': body_text,
            'body_html': body_html,
            'snippet': message.get('snippet', ''),
            'attachments': attachments,
            'has_attachments': len(attachments) > 0
        }
    
    async def send_message(
        self,
        access_token: str,
        to: List[str],
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> Dict:
        """Send email via Gmail"""
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        service = self._get_service(access_token)
        
        # Create message
        message = MIMEMultipart('alternative')
        message['To'] = ', '.join(to)
        message['Subject'] = subject
        
        if in_reply_to:
            message['In-Reply-To'] = in_reply_to
        if references:
            message['References'] = references
        
        if body_text:
            message.attach(MIMEText(body_text, 'plain'))
        if body_html:
            message.attach(MIMEText(body_html, 'html'))
        
        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send
        result = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return result


gmail_service = GmailService()
