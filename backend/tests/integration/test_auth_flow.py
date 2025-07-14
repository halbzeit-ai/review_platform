"""
Integration tests for authentication flow
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session"""
    with patch('app.api.auth.get_db') as mock:
        db_session = MagicMock()
        mock.return_value = db_session
        yield db_session


@pytest.fixture
def mock_email_service():
    """Mock email service"""
    with patch('app.api.auth.email_service') as mock:
        mock.send_verification_email.return_value = True
        mock.send_welcome_email.return_value = True
        yield mock


@pytest.fixture
def mock_token_service():
    """Mock token service"""
    with patch('app.api.auth.token_service') as mock:
        mock.generate_verification_token.return_value = ("test_token", "2024-12-31 23:59:59")
        mock.hash_token.return_value = "hashed_token"
        mock.is_token_expired.return_value = False
        yield mock


class TestAuthFlow:
    """Integration tests for authentication flow"""
    
    def test_registration_with_german_language(self, client, mock_db, mock_email_service, mock_token_service):
        """Test user registration with German language preference"""
        # Mock user doesn't exist
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        registration_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "company_name": "Test Company",
            "role": "startup",
            "preferred_language": "de"
        }
        
        response = client.post("/auth/register", json=registration_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["email"] == "test@example.com"
        assert response_data["company_name"] == "Test Company"
        assert response_data["role"] == "startup"
        
        # Verify email service was called with German language
        mock_email_service.send_verification_email.assert_called_once_with(
            "test@example.com", 
            "test_token", 
            "de"
        )
    
    def test_registration_with_english_language(self, client, mock_db, mock_email_service, mock_token_service):
        """Test user registration with English language preference"""
        # Mock user doesn't exist
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        registration_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "company_name": "Test Company",
            "role": "startup",
            "preferred_language": "en"
        }
        
        response = client.post("/auth/register", json=registration_data)
        
        assert response.status_code == 200
        
        # Verify email service was called with English language
        mock_email_service.send_verification_email.assert_called_once_with(
            "test@example.com", 
            "test_token", 
            "en"
        )
    
    def test_email_verification_sends_welcome_in_user_language(self, client, mock_db, mock_email_service, mock_token_service):
        """Test email verification sends welcome email in user's preferred language"""
        # Mock user with German language preference
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.company_name = "Test Company"
        mock_user.preferred_language = "de"
        mock_user.is_verified = False
        mock_user.verification_token = "hashed_token"
        mock_user.verification_token_expires = "2024-12-31 23:59:59"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        response = client.get("/auth/verify-email?token=test_token")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["verified"] is True
        assert response_data["email"] == "test@example.com"
        
        # Verify welcome email was sent in German
        mock_email_service.send_welcome_email.assert_called_once_with(
            "test@example.com", 
            "Test Company", 
            "de"
        )
        
        # Verify user was marked as verified
        assert mock_user.is_verified is True
        assert mock_user.verification_token is None
        assert mock_user.verification_token_expires is None
    
    def test_email_verification_with_invalid_token(self, client, mock_db, mock_email_service, mock_token_service):
        """Test email verification with invalid token"""
        # Mock no user found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        response = client.get("/auth/verify-email?token=invalid_token")
        
        assert response.status_code == 400
        response_data = response.json()
        assert "Invalid or expired" in response_data["detail"]
        
        # Verify no welcome email was sent
        mock_email_service.send_welcome_email.assert_not_called()
    
    def test_email_verification_with_expired_token(self, client, mock_db, mock_email_service, mock_token_service):
        """Test email verification with expired token"""
        # Mock user with expired token
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.verification_token_expires = "2024-01-01 00:00:00"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_token_service.is_token_expired.return_value = True
        
        response = client.get("/auth/verify-email?token=expired_token")
        
        assert response.status_code == 400
        response_data = response.json()
        assert "expired" in response_data["detail"].lower()
        
        # Verify no welcome email was sent
        mock_email_service.send_welcome_email.assert_not_called()
    
    def test_language_preference_update(self, client, mock_db):
        """Test language preference update endpoint"""
        # Mock authenticated user
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.preferred_language = "en"
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            response = client.post(
                "/auth/language-preference",
                json={"preferred_language": "de"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["preferred_language"] == "de"
            assert response_data["email"] == "test@example.com"
            
            # Verify user's language preference was updated
            assert mock_user.preferred_language == "de"
    
    def test_language_preference_invalid_language(self, client, mock_db):
        """Test language preference update with invalid language"""
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            response = client.post(
                "/auth/language-preference",
                json={"preferred_language": "fr"}  # Unsupported language
            )
            
            assert response.status_code == 400
            response_data = response.json()
            assert "Invalid language" in response_data["detail"]