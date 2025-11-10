from cryptography.fernet import Fernet
from src.config import settings


class EncryptionService:
    def __init__(self):
        self.cipher = Fernet(settings.FERNET_KEY.encode())
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64 encoded encrypted data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded encrypted data and return original string"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()


encryption_service = EncryptionService()
