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
        
        # Language-specific content
        if language == "de":
            subject = "Verifizieren Sie Ihr HALBZEIT AI Konto"
            welcome_text = "Willkommen bei HALBZEIT AI!"
            thank_you_text = "Vielen Dank für Ihre Registrierung bei unserer Startup-Review-Plattform. Um Ihre Registrierung abzuschließen und Ihr Konto zu nutzen, bestätigen Sie bitte Ihre E-Mail-Adresse."
            button_text = "E-Mail-Adresse verifizieren"
            important_text = "Wichtig:"
            expiry_text = "Dieser Verifizierungslink läuft in 24 Stunden ab. Wenn Sie nicht innerhalb dieser Zeit verifizieren, müssen Sie sich erneut registrieren."
            fallback_text = "Wenn die Schaltfläche oben nicht funktioniert, können Sie diesen Link kopieren und in Ihren Browser einfügen:"
            ignore_text = "Wenn Sie kein Konto bei uns erstellt haben, ignorieren Sie diese E-Mail bitte."
            footer_text = "Diese E-Mail wurde von HALBZEIT AI Review Platform gesendet"
            support_text = "Wenn Sie Fragen haben, wenden Sie sich bitte an unser Support-Team."
        else:
            subject = "Verify your HALBZEIT AI account"
            welcome_text = "Welcome to HALBZEIT AI!"
            thank_you_text = "Thank you for registering with our startup review platform. To complete your registration and start using your account, please verify your email address."
            button_text = "Verify Email Address"
            important_text = "Important:"
            expiry_text = "This verification link will expire in 24 hours. If you don't verify within this time, you'll need to register again."
            fallback_text = "If the button above doesn't work, you can copy and paste this link into your browser:"
            ignore_text = "If you didn't create an account with us, please ignore this email."
            footer_text = "This email was sent by HALBZEIT AI Review Platform"
            support_text = "If you have any questions, please contact our support team."
        
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
        if language == "de":
            text_body = f"""
        Willkommen bei HALBZEIT AI!
        
        Vielen Dank für Ihre Registrierung bei unserer Startup-Review-Plattform. Um Ihre Registrierung abzuschließen, bestätigen Sie bitte Ihre E-Mail-Adresse, indem Sie auf den folgenden Link klicken:
        
        {verification_url}
        
        Dieser Verifizierungslink läuft in 24 Stunden ab.
        
        Wenn Sie kein Konto bei uns erstellt haben, ignorieren Sie diese E-Mail bitte.
        
        Mit freundlichen Grüßen,
        HALBZEIT AI Team
        """
        else:
            text_body = f"""
        Welcome to HALBZEIT AI!
        
        Thank you for registering with our startup review platform. To complete your registration, please verify your email address by clicking the link below:
        
        {verification_url}
        
        This verification link will expire in 24 hours.
        
        If you didn't create an account with us, please ignore this email.
        
        Best regards,
        HALBZEIT AI Team
        """
        
        return self.send_email(email, subject, html_body, text_body)

    def send_welcome_email(self, email: str, company_name: str, language: str = "en") -> bool:
        """Send welcome email after successful verification"""
        
        # Language-specific content
        if language == "de":
            subject = "Willkommen bei HALBZEIT AI - Ihr Konto ist bereit!"
            welcome_title = f"🎉 Willkommen bei HALBZEIT AI, {company_name}!"
            verified_text = "Ihre E-Mail wurde erfolgreich verifiziert und Ihr Konto ist nun aktiv. Sie können unsere KI-gestützte Startup-Review-Plattform sofort nutzen."
            features_title = "Was Sie jetzt tun können:"
            upload_text = "📄 Laden Sie Ihr Pitch Deck für KI-Analyse hoch"
            review_text = "🤖 Erhalten Sie detaillierte VC-Style-Reviews powered by KI"
            qa_text = "💬 Führen Sie Q&A mit General Partners"
            track_text = "📊 Verfolgen Sie Ihren Review-Fortschritt"
            login_button = "Bei Ihrem Konto anmelden"
            excited_text = "Wir freuen uns darauf, Ihnen wertvolles Feedback zu Ihrem Startup zu geben!"
        else:
            subject = "Welcome to HALBZEIT AI - Your account is ready!"
            welcome_title = f"🎉 Welcome to HALBZEIT AI, {company_name}!"
            verified_text = "Your email has been successfully verified and your account is now active. You can start using our AI-powered startup review platform immediately."
            features_title = "What you can do now:"
            upload_text = "📄 Upload your pitch deck for AI analysis"
            review_text = "🤖 Get detailed VC-style reviews powered by AI"
            qa_text = "💬 Engage in Q&A with General Partners"
            track_text = "📊 Track your review progress"
            login_button = "Login to Your Account"
            excited_text = "We're excited to help you get valuable feedback on your startup!"
        
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