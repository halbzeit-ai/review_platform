"""
Token service for generating and validating email verification tokens
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from ..core.config import settings

class TokenService:
    @staticmethod
    def generate_verification_token() -> Tuple[str, datetime]:
        """
        Generate a secure verification token and its expiration time
        Returns: (token, expiration_datetime)
        """
        # Generate a cryptographically secure random token
        token = secrets.token_urlsafe(32)
        
        # Set expiration to 24 hours from now
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        return token, expires_at
    
    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash a token for secure storage in database
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def verify_token(token: str, stored_hash: str, expires_at: Optional[datetime]) -> bool:
        """
        Verify that a token matches the stored hash and hasn't expired
        """
        if not token or not stored_hash or not expires_at:
            return False
        
        # Check if token has expired
        if datetime.utcnow() > expires_at:
            return False
        
        # Verify token hash
        token_hash = TokenService.hash_token(token)
        return secrets.compare_digest(token_hash, stored_hash)
    
    @staticmethod
    def is_token_expired(expires_at: Optional[datetime]) -> bool:
        """
        Check if a token has expired
        """
        if not expires_at:
            return True
        return datetime.utcnow() > expires_at

token_service = TokenService()