"""
Email service for sending verification emails using Hetzner SMTP
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import logging
from typing import Optional
from ..core.config import settings
from .i18n_service import i18n_service

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

    def send_email(self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send an email using Hetzner SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = to_email

            # Add text version if provided
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)

            # Add HTML version
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_verification_email(self, email: str, verification_token: str, language: str = "en") -> bool:
        """Send email verification email"""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        # Get translations using I18n service
        subject = i18n_service.t("emails.verification.subject", language)
        welcome_text = i18n_service.t("emails.verification.welcome", language)
        thank_you_text = i18n_service.t("emails.verification.thank_you", language)
        button_text = i18n_service.t("emails.verification.button_text", language)
        important_text = i18n_service.t("emails.verification.important", language)
        expiry_text = i18n_service.t("emails.verification.expiry", language)
        fallback_text = i18n_service.t("emails.verification.fallback", language)
        ignore_text = i18n_service.t("emails.verification.ignore", language)
        footer_text = i18n_service.t("emails.verification.footer", language)
        support_text = i18n_service.t("emails.verification.support", language)
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html lang="{language}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Account</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                    border-bottom: 2px solid #1976d2;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1976d2;
                }}
                .content {{
                    padding: 30px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #1976d2;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 10px;
                    border-radius: 4px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">HALBZEIT AI</div>
                <div>Startup Review Platform</div>
            </div>
            
            <div class="content">
                <h2>{welcome_text}</h2>
                
                <p>{thank_you_text}</p>
                
                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">{button_text}</a>
                </p>
                
                <div class="warning">
                    <strong>{important_text}</strong> {expiry_text}
                </div>
                
                <p>{fallback_text}</p>
                <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                    {verification_url}
                </p>
                
                <p>{ignore_text}</p>
            </div>
            
            <div class="footer">
                <p>{footer_text}</p>
                <p>{support_text}</p>
            </div>
        </body>
        </html>
        """
        
        # Text version for email clients that don't support HTML
        text_welcome = i18n_service.t("emails.verification.text_welcome", language)
        text_thank_you = i18n_service.t("emails.verification.text_thank_you", language)
        text_expiry = i18n_service.t("emails.verification.text_expiry", language)
        text_ignore = i18n_service.t("emails.verification.text_ignore", language)
        text_regards = i18n_service.t("emails.verification.text_regards", language)
        
        text_body = f"""
        {text_welcome}
        
        {text_thank_you}
        
        {verification_url}
        
        {text_expiry}
        
        {text_ignore}
        
        {text_regards}
        """
        
        return self.send_email(email, subject, html_body, text_body)

    def send_welcome_email(self, email: str, company_name: str, language: str = "en") -> bool:
        """Send welcome email after successful verification"""
        
        # Get translations using I18n service
        subject = i18n_service.t("emails.welcome.subject", language)
        welcome_title = i18n_service.t("emails.welcome.title", language, company_name=company_name)
        verified_text = i18n_service.t("emails.welcome.verified", language)
        features_title = i18n_service.t("emails.welcome.features_title", language)
        upload_text = i18n_service.t("emails.welcome.feature_upload", language)
        review_text = i18n_service.t("emails.welcome.feature_review", language)
        qa_text = i18n_service.t("emails.welcome.feature_qa", language)
        track_text = i18n_service.t("emails.welcome.feature_track", language)
        login_button = i18n_service.t("emails.welcome.login_button", language)
        excited_text = i18n_service.t("emails.welcome.excited", language)
        
        html_body = f"""
        <!DOCTYPE html>
        <html lang="{language}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to HALBZEIT AI</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                    border-bottom: 2px solid #1976d2;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1976d2;
                }}
                .content {{
                    padding: 30px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #1976d2;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .features {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .feature-item {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">HALBZEIT AI</div>
                <div>Startup Review Platform</div>
            </div>
            
            <div class="content">
                <h2>{welcome_title}</h2>
                
                <p>{verified_text}</p>
                
                <div class="features">
                    <h3>{features_title}</h3>
                    <div class="feature-item">{upload_text}</div>
                    <div class="feature-item">{review_text}</div>
                    <div class="feature-item">{qa_text}</div>
                    <div class="feature-item">{track_text}</div>
                </div>
                
                <p style="text-align: center;">
                    <a href="{settings.FRONTEND_URL}/login" class="button">{login_button}</a>
                </p>
                
                <p>{excited_text}</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, html_body)

# Global email service instance
email_service = EmailService()