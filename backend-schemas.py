from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    OWNER = "owner"
    MEMBER = "member"


class EmailProvider(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# Email Account Schemas
class EmailAccountBase(BaseModel):
    email_address: str
    display_name: Optional[str] = None
    provider: EmailProvider


class EmailAccountCreate(EmailAccountBase):
    pass


class EmailAccount(EmailAccountBase):
    id: int
    user_id: int
    is_active: bool
    last_synced_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Message Schemas
class AttachmentSchema(BaseModel):
    id: int
    filename: str
    size: Optional[int] = None
    mime_type: Optional[str] = None
    provider_attachment_id: str

    class Config:
        from_attributes = True


class MessageSchema(BaseModel):
    id: int
    provider_message_id: str
    from_addr: str
    to_addrs: List[str]
    cc_addrs: List[str] = []
    bcc_addrs: List[str] = []
    subject: Optional[str] = None
    date: datetime
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    has_attachments: bool
    is_read: bool
    attachments: List[AttachmentSchema] = []

    class Config:
        from_attributes = True


class ThreadSchema(BaseModel):
    id: int
    account_id: int
    provider_thread_id: str
    subject: Optional[str] = None
    snippet: Optional[str] = None
    last_message_at: datetime
    messages: List[MessageSchema] = []

    class Config:
        from_attributes = True


class InboxMessageSchema(BaseModel):
    id: int
    thread_id: int
    account_id: int
    account_email: str
    provider: EmailProvider
    from_addr: str
    subject: Optional[str] = None
    snippet: Optional[str] = None
    date: datetime
    has_attachments: bool
    is_read: bool

    class Config:
        from_attributes = True


# Send Message Schema
class SendMessageRequest(BaseModel):
    account_id: int
    to: List[str]
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
