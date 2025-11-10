from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://unifiedinbox:password@localhost/unifiedinbox"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str
    FERNET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    BASE_URL: str = "http://localhost"
    ENVIRONMENT: str = "development"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = ""
    
    # Microsoft OAuth
    MS_CLIENT_ID: str
    MS_CLIENT_SECRET: str
    MS_TENANT: str = "common"
    MS_REDIRECT_URI: str = ""
    
    # Email Sync
    SYNC_INTERVAL_MINUTES: int = 5
    MAX_MESSAGES_PER_ACCOUNT: int = 50
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost"]
    
    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set redirect URIs based on BASE_URL
        if not self.GOOGLE_REDIRECT_URI:
            self.GOOGLE_REDIRECT_URI = f"{self.BASE_URL}/api/v1/oauth/gmail/callback"
        if not self.MS_REDIRECT_URI:
            self.MS_REDIRECT_URI = f"{self.BASE_URL}/api/v1/oauth/outlook/callback"
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL


settings = Settings()
