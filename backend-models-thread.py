from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_thread_id = Column(String, nullable=False, index=True)
    subject = Column(Text)
    snippet = Column(Text)
    last_message_at = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    account = relationship("EmailAccount", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
