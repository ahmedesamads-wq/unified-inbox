from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base
import enum


class EmailProvider(str, enum.Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(Enum(EmailProvider), nullable=False)
    email_address = Column(String, nullable=False, index=True)
    display_name = Column(String)
    access_token = Column(Text)
    encrypted_refresh_token = Column(Text)
    token_expiry = Column(DateTime(timezone=True))
    sync_state = Column(JSON, default={})  # Stores historyId for Gmail, deltaLink for Outlook
    last_synced_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="email_accounts")
    threads = relationship("Thread", back_populates="account", cascade="all, delete-orphan")
