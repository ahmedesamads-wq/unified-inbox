from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base
import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    email_accounts = relationship("EmailAccount", back_populates="user", cascade="all, delete-orphan")
