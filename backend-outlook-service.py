from datetime import datetime
from typing import Optional, List, Dict
import httpx
from src.config import settings


class OutlookService:
    def __init__(self):
        self.client_id = settings.MS_CLIENT_ID
        self.client_secret = settings.MS_CLIENT_SECRET
        self.redirect_uri = settings.MS_REDIRECT_URI
        self.tenant = settings.MS_TENANT
        self.scopes = ['Mail.Read', 'Mail.Send', 'offline_access']
    
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL"""
        scope_str = ' '.join(self.scopes)
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': scope_str,
            'state': state,
            'response_mode': 'query'
        }
        query = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f'https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/authorize?{query}'
    
    async def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access and refresh tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token',
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'redirect_uri': self.redirect_uri,
                    'grant_type': 'authorization_code',
                    'scope': ' '.join(self.scopes)
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token',
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                    'scope': ' '.join(self.scopes)
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_profile(self, access_token: str) -> Dict:
        """Get user's email address and profile info"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            response.raise_for_status()
            return response.json()
    
    async def fetch_messages(
        self,
        access_token: str,
        max_results: int = 50,
        delta_link: Optional[str] = None
    ) -> Dict:
        """Fetch messages from Outlook"""
        async with httpx.AsyncClient() as client:
            if delta_link:
                # Incremental sync using delta
                response = await client.get(
                    delta_link,
                    headers={'Authorization': f'Bearer {access_token}'}
                )
            else:
                # Full sync - get recent messages
                response = await client.get(
                    f'https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages/delta?$top={max_results}',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                'messages': data.get('value', []),
                'delta_link': data.get('@odata.deltaLink'),
                'next_link': data.get('@odata.nextLink')
            }
    
    def parse_message(self, message: Dict) -> Dict:
        """Parse Outlook message into standardized format"""
        # Parse date
        date_str = message.get('receivedDateTime', message.get('sentDateTime', ''))
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            date = datetime.utcnow()
        
        # Extract recipients
        to_addrs = [r['emailAddress']['address'] for r in message.get('toRecipients', [])]
        cc_addrs = [r['emailAddress']['address'] for r in message.get('ccRecipients', [])]
        bcc_addrs = [r['emailAddress']['address'] for r in message.get('bccRecipients', [])]
        
        # Extract from
        from_addr = message.get('from', {}).get('emailAddress', {}).get('address', '')
        
        # Extract body
        body_obj = message.get('body', {})
        body_html = '' if body_obj.get('contentType') == 'html' else ''
        body_text = '' if body_obj.get('contentType') == 'text' else ''
        
        if body_obj.get('contentType') == 'html':
            body_html = body_obj.get('content', '')
        else:
            body_text = body_obj.get('content', '')
        
        # Extract attachments
        attachments = []
        if message.get('hasAttachments'):
            for att in message.get('attachments', []):
                attachments.append({
                    'filename': att.get('name', ''),
                    'mime_type': att.get('contentType', ''),
                    'size': att.get('size', 0),
                    'attachment_id': att.get('id', '')
                })
        
        # Conversation/thread ID
        thread_id = message.get('conversationId', message.get('id'))
        
        return {
            'provider_message_id': message['id'],
            'thread_id': thread_id,
            'from_addr': from_addr,
            'to_addrs': to_addrs,
            'cc_addrs': cc_addrs,
            'bcc_addrs': bcc_addrs,
            'subject': message.get('subject', ''),
            'date': date,
            'body_text': body_text,
            'body_html': body_html,
            'snippet': message.get('bodyPreview', ''),
            'attachments': attachments,
            'has_attachments': message.get('hasAttachments', False)
        }
    
    async def send_message(
        self,
        access_token: str,
        to: List[str],
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        in_reply_to: Optional[str] = None
    ) -> Dict:
        """Send email via Outlook"""
        # Prepare message body
        body_content = body_html if body_html else body_text
        content_type = 'HTML' if body_html else 'Text'
        
        message_data = {
            'message': {
                'subject': subject,
                'body': {
                    'contentType': content_type,
                    'content': body_content
                },
                'toRecipients': [
                    {'emailAddress': {'address': addr}} for addr in to
                ]
            }
        }
        
        async with httpx.AsyncClient() as client:
            if in_reply_to:
                # Reply to existing message
                response = await client.post(
                    f'https://graph.microsoft.com/v1.0/me/messages/{in_reply_to}/reply',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    },
                    json={'comment': body_content}
                )
            else:
                # Send new message
                response = await client.post(
                    'https://graph.microsoft.com/v1.0/me/sendMail',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    },
                    json=message_data
                )
            
            response.raise_for_status()
            return {'status': 'sent'}


outlook_service = OutlookService()
