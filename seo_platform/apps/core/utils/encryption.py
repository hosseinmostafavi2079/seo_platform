# apps/core/utils/encryption.py
import os
from cryptography.fernet import Fernet
from django.conf import settings

class EncryptedFieldHelper:
    @staticmethod
    def _get_fernet():
        # خواندن کلید فرنت از تنظیمات جنگو که از .env لود می‌شود
        key = getattr(settings, 'FERNET_KEY', None)
        if not key or key == "":
            # یک کلید فال‌بک موقت برای زمان مایگریشن یا لوکال دِو
            return Fernet(Fernet.generate_key())
        return Fernet(key.encode())

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        if not plaintext:
            return ""
        f = cls._get_fernet()
        return f.encrypt(plaintext.encode()).decode()

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            f = cls._get_fernet()
            return f.decrypt(ciphertext.encode()).decode()
        except Exception:
            return "[Error: Decryption Failed]"