from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_message_id = Column(String, nullable=False, unique=True, index=True)
    from_addr = Column(String, nullable=False)
    to_addrs = Column(JSON, default=[])
    cc_addrs = Column(JSON, default=[])
    bcc_addrs = Column(JSON, default=[])
    subject = Column(Text)
    date = Column(DateTime(timezone=True), index=True)
    body_text = Column(Text)
    body_html = Column(Text)
    has_attachments = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    size = Column(Integer)
    mime_type = Column(String)
    provider_attachment_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    message = relationship("Message", back_populates="attachments")
