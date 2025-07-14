"""
Pytest configuration and fixtures for the test suite
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add the backend app to the path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


@pytest.fixture(scope="session")
def mock_settings():
    """Mock settings for all tests"""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.SMTP_SERVER = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USERNAME = "test@example.com"
        mock_settings.SMTP_PASSWORD = "password"
        mock_settings.FROM_EMAIL = "noreply@example.com"
        mock_settings.FROM_NAME = "Test Service"
        mock_settings.FRONTEND_URL = "https://example.com"
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        yield mock_settings


@pytest.fixture
def mock_i18n_translations():
    """Mock i18n translations for testing"""
    return {
        "en": {
            "emails": {
                "verification": {
                    "subject": "Verify your HALBZEIT AI account",
                    "welcome": "Welcome to HALBZEIT AI!",
                    "thank_you": "Thank you for registering with our startup review platform.",
                    "button_text": "Verify Email Address",
                    "important": "Important:",
                    "expiry": "This verification link will expire in 24 hours.",
                    "fallback": "If the button above doesn't work, copy and paste this link:",
                    "ignore": "If you didn't create an account with us, please ignore this email.",
                    "footer": "This email was sent by HALBZEIT AI Review Platform",
                    "support": "If you have any questions, please contact our support team.",
                    "text_welcome": "Welcome to HALBZEIT AI!",
                    "text_thank_you": "Thank you for registering. Click the link below to verify:",
                    "text_expiry": "This verification link will expire in 24 hours.",
                    "text_ignore": "If you didn't create an account, ignore this email.",
                    "text_regards": "Best regards,\nHALBZEIT AI Team"
                },
                "welcome": {
                    "subject": "Welcome to HALBZEIT AI - Your account is ready!",
                    "title": "🎉 Welcome to HALBZEIT AI, {company_name}!",
                    "verified": "Your email has been successfully verified.",
                    "features_title": "What you can do now:",
                    "feature_upload": "📄 Upload your pitch deck for AI analysis",
                    "feature_review": "🤖 Get detailed VC-style reviews powered by AI",
                    "feature_qa": "💬 Engage in Q&A with General Partners",
                    "feature_track": "📊 Track your review progress",
                    "login_button": "Login to Your Account",
                    "excited": "We're excited to help you get valuable feedback on your startup!"
                }
            }
        },
        "de": {
            "emails": {
                "verification": {
                    "subject": "Verifizieren Sie Ihr HALBZEIT AI Konto",
                    "welcome": "Willkommen bei HALBZEIT AI!",
                    "thank_you": "Vielen Dank für Ihre Registrierung bei unserer Startup-Review-Plattform.",
                    "button_text": "E-Mail-Adresse verifizieren",
                    "important": "Wichtig:",
                    "expiry": "Dieser Verifizierungslink läuft in 24 Stunden ab.",
                    "fallback": "Wenn die Schaltfläche oben nicht funktioniert, kopieren Sie diesen Link:",
                    "ignore": "Wenn Sie kein Konto bei uns erstellt haben, ignorieren Sie diese E-Mail.",
                    "footer": "Diese E-Mail wurde von HALBZEIT AI Review Platform gesendet",
                    "support": "Wenn Sie Fragen haben, wenden Sie sich an unser Support-Team.",
                    "text_welcome": "Willkommen bei HALBZEIT AI!",
                    "text_thank_you": "Vielen Dank für Ihre Registrierung. Klicken Sie auf den Link:",
                    "text_expiry": "Dieser Verifizierungslink läuft in 24 Stunden ab.",
                    "text_ignore": "Wenn Sie kein Konto erstellt haben, ignorieren Sie diese E-Mail.",
                    "text_regards": "Mit freundlichen Grüßen,\nHALBZEIT AI Team"
                },
                "welcome": {
                    "subject": "Willkommen bei HALBZEIT AI - Ihr Konto ist bereit!",
                    "title": "🎉 Willkommen bei HALBZEIT AI, {company_name}!",
                    "verified": "Ihre E-Mail wurde erfolgreich verifiziert.",
                    "features_title": "Was Sie jetzt tun können:",
                    "feature_upload": "📄 Laden Sie Ihr Pitch Deck für KI-Analyse hoch",
                    "feature_review": "🤖 Erhalten Sie detaillierte VC-Style-Reviews powered by KI",
                    "feature_qa": "💬 Führen Sie Q&A mit General Partners",
                    "feature_track": "📊 Verfolgen Sie Ihren Review-Fortschritt",
                    "login_button": "Bei Ihrem Konto anmelden",
                    "excited": "Wir freuen uns darauf, Ihnen wertvolles Feedback zu geben!"
                }
            }
        }
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "company_name": "Test Company",
        "role": "startup",
        "preferred_language": "en"
    }