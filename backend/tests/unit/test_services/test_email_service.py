"""
Unit tests for Email service functionality
"""

import pytest
from unittest.mock import patch, MagicMock
from email.mime.multipart import MIMEMultipart

from app.services.email_service import EmailService


class TestEmailService:
    """Test cases for EmailService"""
    
    def test_service_initialization(self):
        """Test email service initialization"""
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.SMTP_SERVER = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "test@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.FROM_EMAIL = "noreply@example.com"
            mock_settings.FROM_NAME = "Test Service"
            
            service = EmailService()
            assert service.smtp_server == "smtp.example.com"
            assert service.smtp_port == 587
            assert service.username == "test@example.com"
    
    @patch('app.services.email_service.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=None)
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.SMTP_SERVER = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "test@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.FROM_EMAIL = "noreply@example.com"
            mock_settings.FROM_NAME = "Test Service"
            
            service = EmailService()
            result = service.send_email("recipient@example.com", "Test Subject", "<h1>Test HTML</h1>", "Test Text")
            
            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@example.com", "password")
            mock_server.send_message.assert_called_once()
    
    @patch('app.services.email_service.smtplib.SMTP')
    def test_send_email_failure(self, mock_smtp):
        """Test email sending failure"""
        # Mock SMTP server to raise exception
        mock_smtp.side_effect = Exception("SMTP Error")
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.SMTP_SERVER = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "test@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.FROM_EMAIL = "noreply@example.com"
            mock_settings.FROM_NAME = "Test Service"
            
            service = EmailService()
            result = service.send_email("recipient@example.com", "Test Subject", "<h1>Test HTML</h1>")
            
            assert result is False
    
    @patch.object(EmailService, 'send_email')
    @patch('app.services.email_service.i18n_service')
    def test_send_verification_email_english(self, mock_i18n, mock_send):
        """Test verification email generation in English"""
        # Mock i18n service responses
        mock_i18n.t.side_effect = lambda key, lang: {
            "emails.verification.subject": "Verify your HALBZEIT AI account",
            "emails.verification.welcome": "Welcome to HALBZEIT AI!",
            "emails.verification.thank_you": "Thank you for registering...",
            "emails.verification.button_text": "Verify Email Address",
            "emails.verification.important": "Important:",
            "emails.verification.expiry": "This link will expire in 24 hours",
            "emails.verification.fallback": "If button doesn't work...",
            "emails.verification.ignore": "If you didn't create account...",
            "emails.verification.footer": "This email was sent by HALBZEIT AI",
            "emails.verification.support": "Contact support...",
            "emails.verification.text_welcome": "Welcome to HALBZEIT AI!",
            "emails.verification.text_thank_you": "Thank you for registering...",
            "emails.verification.text_expiry": "Link expires in 24 hours",
            "emails.verification.text_ignore": "Ignore if not yours",
            "emails.verification.text_regards": "Best regards, HALBZEIT AI Team"
        }[key]
        
        mock_send.return_value = True
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.FRONTEND_URL = "https://example.com"
            mock_settings.SMTP_SERVER = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "test@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.FROM_EMAIL = "noreply@example.com"
            mock_settings.FROM_NAME = "Test Service"
            
            service = EmailService()
            result = service.send_verification_email("test@example.com", "test_token", "en")
            
            assert result is True
            mock_send.assert_called_once()
            
            # Check that send_email was called with correct parameters
            call_args = mock_send.call_args
            assert call_args[0][0] == "test@example.com"  # recipient
            assert "Verify your HALBZEIT AI account" in call_args[0][1]  # subject
            assert "Welcome to HALBZEIT AI!" in call_args[0][2]  # html body
    
    @patch.object(EmailService, 'send_email')
    @patch('app.services.email_service.i18n_service')
    def test_send_verification_email_german(self, mock_i18n, mock_send):
        """Test verification email generation in German"""
        # Mock i18n service responses for German
        mock_i18n.t.side_effect = lambda key, lang: {
            "emails.verification.subject": "Verifizieren Sie Ihr HALBZEIT AI Konto",
            "emails.verification.welcome": "Willkommen bei HALBZEIT AI!",
            "emails.verification.thank_you": "Vielen Dank für Ihre Registrierung...",
            "emails.verification.button_text": "E-Mail-Adresse verifizieren",
            "emails.verification.important": "Wichtig:",
            "emails.verification.expiry": "Link läuft in 24 Stunden ab",
            "emails.verification.fallback": "Falls Button nicht funktioniert...",
            "emails.verification.ignore": "Falls Sie kein Konto erstellt haben...",
            "emails.verification.footer": "Diese E-Mail wurde von HALBZEIT AI gesendet",
            "emails.verification.support": "Support kontaktieren...",
            "emails.verification.text_welcome": "Willkommen bei HALBZEIT AI!",
            "emails.verification.text_thank_you": "Vielen Dank für Registrierung...",
            "emails.verification.text_expiry": "Link läuft in 24 Stunden ab",
            "emails.verification.text_ignore": "Ignorieren falls nicht Ihrs",
            "emails.verification.text_regards": "Mit freundlichen Grüßen, HALBZEIT AI Team"
        }[key]
        
        mock_send.return_value = True
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.FRONTEND_URL = "https://example.com"
            mock_settings.SMTP_SERVER = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "test@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.FROM_EMAIL = "noreply@example.com"
            mock_settings.FROM_NAME = "Test Service"
            
            service = EmailService()
            result = service.send_verification_email("test@example.com", "test_token", "de")
            
            assert result is True
            mock_send.assert_called_once()
            
            # Check that send_email was called with German content
            call_args = mock_send.call_args
            assert call_args[0][0] == "test@example.com"  # recipient
            assert "Verifizieren Sie Ihr HALBZEIT AI Konto" in call_args[0][1]  # subject
            assert "Willkommen bei HALBZEIT AI!" in call_args[0][2]  # html body
    
    @patch.object(EmailService, 'send_email')
    @patch('app.services.email_service.i18n_service')
    def test_send_welcome_email_with_company_name(self, mock_i18n, mock_send):
        """Test welcome email with company name substitution"""
        # Mock i18n service responses with variable substitution
        def mock_translate(key, lang, **kwargs):
            if key == "emails.welcome.title":
                return f"🎉 Welcome to HALBZEIT AI, {kwargs.get('company_name', 'Company')}!"
            return "Mock Translation"
        
        mock_i18n.t = mock_translate
        mock_send.return_value = True
        
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.FRONTEND_URL = "https://example.com"
            mock_settings.SMTP_SERVER = "smtp.example.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "test@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.FROM_EMAIL = "noreply@example.com"
            mock_settings.FROM_NAME = "Test Service"
            
            service = EmailService()
            result = service.send_welcome_email("test@example.com", "Test Company", "en")
            
            assert result is True
            mock_send.assert_called_once()
            
            # Check that company name was substituted
            call_args = mock_send.call_args
            assert "Test Company" in call_args[0][2]  # html body should contain company name